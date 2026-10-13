"""Os testes correm numa base própria (contentdeck_test), criada do zero a cada sessão
e carregada com o CSV de exemplo. A base real nunca é tocada."""
import os
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
BASE_URL = make_url(os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/contentdeck"))
TEST_URL = BASE_URL.set(database="contentdeck_test")
# tem de ser definido antes de importar db/ingest/migrate, que leem a variável ao carregar
os.environ["DATABASE_URL"] = TEST_URL.render_as_string(hide_password=False)


@pytest.fixture(scope="session", autouse=True)
def database():
    admin = create_engine(BASE_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS contentdeck_test WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE contentdeck_test"))

    import ingest
    import migrate

    migrate.main()
    ingest.process_csv(str(ROOT / "data" / "instagram_export.csv"), "instagram", "exemplo",
                       captured_on=date(2026, 6, 10))
    # segunda captura, mais antiga, com números menores: as rotas devem ignorá-la
    with ingest.engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO metrics (post_id, captured_on, views, reach, likes, engagement_rate)
            SELECT id, DATE '2026-06-03', 10, 10, 1, 0.1 FROM posts
        """))
        conn.execute(text("UPDATE posts SET theme = 'cinema' WHERE external_id <> '90000000000000002'"))
        conn.execute(text("UPDATE posts SET theme = 'edicao' WHERE external_id = '90000000000000002'"))
    yield
    ingest.engine.dispose()
    migrate.engine.dispose()
    import db
    db.engine.dispose()
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS contentdeck_test WITH (FORCE)"))
    admin.dispose()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    import api

    return TestClient(api.app)
