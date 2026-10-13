"""Testes do que já está implementado. Devem passar sempre: pytest tests/test_api.py"""
from datetime import date

import pytest
from sqlalchemy import text

import ingest


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_summary(client):
    r = client.get("/profiles/exemplo/summary")
    assert r.status_code == 200
    s = r.json()
    assert s["posts"] == 3
    assert s["captured_on"] == "2026-06-10"
    assert s["views"] == 14000 + 9100 + 5500      # só a captura mais recente de cada post
    assert s["follows"] == 35 + 12 + 4
    assert s["median_views"] == 9100
    assert s["top_post_share"] == pytest.approx(14000 / 28600)


def test_summary_perfil_inexistente(client):
    assert client.get("/profiles/ninguem/summary").status_code == 404


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
