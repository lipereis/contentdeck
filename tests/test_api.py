"""Testes da carga e da API.

Dados de teste (CSV de exemplo, captura de 10/06/2026):
  post 001  01/06 (seg)  42 s  views 14000  alcance 12500  eng 0.0888  follows 35  tema cinema  variante com
  post 002  05/06 (sex)  18 s  views  9100  alcance  8400  eng 0.1006  follows 12  tema edicao  variante sem
  post 003  10/06 (qua)  75 s  views  5500  alcance  5200  eng 0.1044  follows  4  tema cinema  variante sem
Existe ainda uma captura antiga (03/06) com 10 views por post, que só pode aparecer no histórico.
"""
from datetime import date

import pytest
from sqlalchemy import text

import ingest

BASE = "/profiles/exemplo"


# ---------- carga ----------

def test_recarregar_nao_duplica():
    with ingest.engine.connect() as conn:
        antes = conn.execute(text("SELECT count(*) FROM metrics")).scalar()
    ingest.process_csv("data/instagram_export.csv", "instagram", "exemplo", captured_on=date(2026, 6, 10))
    with ingest.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM metrics")).scalar() == antes


def test_data_da_captura_vem_do_nome_do_ficheiro():
    assert ingest.capture_date("data/Sep-15-2026_Oct-12-2026_2156508362410637.csv") == date(2026, 10, 12)
    assert ingest.capture_date("data/qualquer.csv") == date.today()


def test_data_de_publicacao_e_mes_dia_ano():
    with ingest.engine.connect() as conn:
        dia = conn.execute(text(
            "SELECT published_at::date FROM posts WHERE external_id = '90000000000000002'")).scalar()
    assert dia == date(2026, 6, 5)   # '06/05/2026' é 5 de junho, não 6 de maio


# ---------- /health e /summary ----------

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_summary(client):
    r = client.get(f"{BASE}/summary")
    assert r.status_code == 200
    s = r.json()
    assert s["posts"] == 3
    assert s["captured_on"] == "2026-06-10"
    assert s["views"] == 14000 + 9100 + 5500      # só a captura mais recente de cada post
    assert s["follows"] == 35 + 12 + 4
    assert s["median_views"] == 9100
    assert s["top_post_share"] == pytest.approx(14000 / 28600)


@pytest.mark.parametrize("rota", ["summary", "posts", "themes", "weekly", "insights", "experiments"])
def test_perfil_inexistente_da_404(client, rota):
    assert client.get(f"/profiles/ninguem/{rota}").status_code == 404


# ---------- /posts ----------

def test_posts_por_data(client):
    r = client.get(f"{BASE}/posts")
    assert r.status_code == 200
    assert [p["views"] for p in r.json()] == [5500, 9100, 14000]   # mais recente primeiro


def test_posts_ordena_por_views(client):
    asc = client.get(f"{BASE}/posts", params={"sort": "views", "order": "asc"}).json()
    assert [p["views"] for p in asc] == [5500, 9100, 14000]
    desc = client.get(f"{BASE}/posts", params={"sort": "views"}).json()
    assert [p["views"] for p in desc] == [14000, 9100, 5500]


def test_posts_ordena_por_engajamento(client):
    posts = client.get(f"{BASE}/posts", params={"sort": "engagement"}).json()
    assert [p["views"] for p in posts] == [5500, 9100, 14000]


def test_posts_filtra_tema_e_limita(client):
    posts = client.get(f"{BASE}/posts", params={"theme": "cinema"}).json()
    assert len(posts) == 2 and {p["theme"] for p in posts} == {"cinema"}
    assert len(client.get(f"{BASE}/posts", params={"limit": 1}).json()) == 1
    assert client.get(f"{BASE}/posts", params={"theme": "nao-existe"}).json() == []


@pytest.mark.parametrize("params", [
    {"sort": "views; DROP TABLE posts"}, {"order": "desc; --"}, {"limit": 0}, {"limit": 1000},
])
def test_posts_rejeita_parametros_invalidos(client, params):
    assert client.get(f"{BASE}/posts", params=params).status_code == 422


# ---------- /posts/{id}/history ----------

def test_historico_do_post(client):
    post = client.get(f"{BASE}/posts", params={"sort": "views"}).json()[0]
    history = client.get(f"/posts/{post['id']}/history").json()
    assert [(c["captured_on"], c["views"]) for c in history] == [("2026-06-03", 10), ("2026-06-10", 14000)]
    assert client.get("/posts/999999/history").status_code == 404


# ---------- /themes e /weekly ----------

def test_temas(client):
    temas = client.get(f"{BASE}/themes").json()
    assert [t["theme"] for t in temas] == ["cinema", "edicao"]   # mais posts primeiro
    cinema, edicao = temas
    assert cinema["posts"] == 2
    assert cinema["median_views"] == (14000 + 5500) / 2
    assert cinema["follows"] == 39
    assert edicao["posts"] == 1 and edicao["median_views"] == 9100
    assert edicao["median_engagement_rate"] == pytest.approx(0.1006, abs=1e-4)


def test_semanas(client):
    semanas = client.get(f"{BASE}/weekly").json()
    assert [s["week_start"] for s in semanas] == ["2026-06-01", "2026-06-08"]
    primeira, segunda = semanas
    assert primeira["posts"] == 2 and primeira["views"] == 23100
    assert primeira["median_views"] == (14000 + 9100) / 2
    assert segunda["posts"] == 1 and segunda["views"] == 5500


# ---------- /insights ----------

def test_insights(client):
    i = client.get(f"{BASE}/insights").json()
    assert i["posts"] == 3 and i["median_views"] == 9100
    assert i["outliers"] == []                          # 14000 não passa de 3 x 9100
    assert i["follows_per_1000_reach"] == pytest.approx(51 / 26100 * 1000)
    assert i["likes_share_of_interactions"] == pytest.approx(1880 / 2498)
    assert i["posts_without_comments"] == 0 and i["posts_without_follows"] == 0
    assert [(b["bucket"], b["posts"], b["median_views"]) for b in i["by_duration"]] == [
        ("até 20 s", 1, 9100), ("21–60 s", 1, 14000), ("mais de 60 s", 1, 5500)]


def test_insights_fora_da_curva(client):
    i = client.get(f"{BASE}/insights", params={"outlier_factor": 1.5}).json()
    assert len(i["outliers"]) == 1
    o = i["outliers"][0]
    assert o["views"] == 14000
    assert o["times_median"] == pytest.approx(14000 / 9100)
    assert o["share_of_views"] == pytest.approx(14000 / 28600)
    assert client.get(f"{BASE}/insights", params={"outlier_factor": 0.5}).status_code == 422


# ---------- /experiments ----------

def test_experimentos(client):
    exps = client.get(f"{BASE}/experiments").json()
    assert len(exps) == 1
    e = exps[0]
    assert e["name"] == "cta-seguir" and e["variable"] == "chamada na legenda"
    com, sem = e["variants"]
    assert (com["variant"], com["posts"], com["median_views"], com["follows"]) == ("com", 1, 14000, 35)
    assert (sem["variant"], sem["posts"], sem["median_views"], sem["follows"]) == ("sem", 2, 7300, 16)
