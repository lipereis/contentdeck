"""Aplica o schema e as migrações pendentes, em ordem, uma única vez cada.

Uso: python migrate.py
schema.SQL é a versão 001; migrations/*.sql vêm depois, em ordem alfabética.
O que já foi aplicado fica registado na tabela schema_migrations.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")
engine = create_engine(os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/contentdeck"))


def main():
    files = [("001_schema", HERE / "schema.SQL")]
    files += [(p.stem, p) for p in sorted((HERE / "migrations").glob("*.sql"))]

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(100) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        applied = {r[0] for r in conn.execute(text("SELECT version FROM schema_migrations"))}

    for version, path in files:
        if version in applied:
            continue
        # cada migração numa transação: ou aplica inteira, ou não aplica nada
        with engine.begin() as conn:
            conn.exec_driver_sql(path.read_text(encoding="utf-8"))
            conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:v)"), {"v": version})
        print(f"aplicada: {version}")

    print("schema em dia.")


if __name__ == "__main__":
    main()
