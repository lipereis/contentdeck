"""Ligação ao Postgres partilhada pela API."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/contentdeck")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def get_conn():
    """Dependência do FastAPI: abre uma ligação por pedido e fecha no fim."""
    with engine.connect() as conn:
        yield conn
