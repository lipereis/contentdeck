"""Testes das rotas por implementar em api.py. Falham até cada exercício ficar pronto.

    pytest tests/test_exercicios.py -k exercicio_1

Dados de teste (CSV de exemplo, captura de 10/06/2026):
  post 001  01/06 (seg)  views 14000  eng 0.0888  follows 35  tema cinema
  post 002  05/06 (sex)  views  9100  eng 0.1006  follows 12  tema edicao
  post 003  10/06 (qua)  views  5500  eng 0.1044  follows  4  tema cinema
Existe ainda uma captura antiga (03/06) com 10 views por post, que não pode aparecer.
"""
import pytest

BASE = "/profiles/exemplo"


# ---------- exercício 1: /posts ----------

def test_exercicio_1_lista_por_data(client):
    r = client.get(f"{BASE}/posts")
    assert r.status_code == 200
    posts = r.json()
    assert [p["views"] for p in posts] == [5500, 9100, 14000]   # mais recente primeiro


def test_exercicio_1_ordena_por_views(client):
    posts = client.get(f"{BASE}/posts", params={"sort": "views", "order": "asc"}).json()
    assert [p["views"] for p in posts] == [5500, 9100, 14000]
    posts = client.get(f"{BASE}/posts", params={"sort": "views"}).json()
    assert [p["views"] for p in posts] == [14000, 9100, 5500]


def test_exercicio_1_ordena_por_engajamento(client):
    posts = client.get(f"{BASE}/posts", params={"sort": "engagement"}).json()
    assert [p["views"] for p in posts] == [5500, 9100, 14000]


def test_exercicio_1_filtra_tema_e_limita(client):
    posts = client.get(f"{BASE}/posts", params={"theme": "cinema"}).json()
    assert len(posts) == 2 and {p["theme"] for p in posts} == {"cinema"}
    assert len(client.get(f"{BASE}/posts", params={"limit": 1}).json()) == 1


def test_exercicio_1_rejeita_ordenacao_invalida(client):
    r = client.get(f"{BASE}/posts", params={"sort": "views; DROP TABLE posts"})
    assert r.status_code == 422


def test_exercicio_1_perfil_inexistente(client):
    assert client.get("/profiles/ninguem/posts").status_code == 404


# ---------- exercício 2: /themes ----------

def test_exercicio_2_temas(client):
    r = client.get(f"{BASE}/themes")
    assert r.status_code == 200
    temas = r.json()
    assert [t["theme"] for t in temas] == ["cinema", "edicao"]   # mais posts primeiro
    cinema, edicao = temas
    assert cinema["posts"] == 2
    assert cinema["median_views"] == (14000 + 5500) / 2
    assert cinema["follows"] == 39
    assert edicao["posts"] == 1 and edicao["median_views"] == 9100
    assert edicao["median_engagement_rate"] == pytest.approx(0.1006, abs=1e-4)


# ---------- exercício 3: /weekly ----------

def test_exercicio_3_semanas(client):
    r = client.get(f"{BASE}/weekly")
    assert r.status_code == 200
    semanas = r.json()
    assert [s["week_start"] for s in semanas] == ["2026-06-01", "2026-06-08"]
    primeira, segunda = semanas
    assert primeira["posts"] == 2 and primeira["views"] == 23100
    assert primeira["median_views"] == (14000 + 9100) / 2
    assert segunda["posts"] == 1 and segunda["views"] == 5500
