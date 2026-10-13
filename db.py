"""Ligação ao Postgres, partilhada pela API e pelos scripts."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

load_dotenv(Path(__file__).resolve().parent / ".env")


def database_url() -> str:
    """URL da base, sempre com o driver psycopg2.

    Serviços geridos (Neon, por exemplo) entregam 'postgres://' ou 'postgresql://';
    sem o driver explícito o SQLAlchemy pode procurar outro que não está instalado.
    """
    url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/contentdeck")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


DATABASE_URL = database_url()
# Em funções serverless cada instância é efémera e a base já tem pooler próprio:
# abrir e fechar por pedido evita ligações penduradas.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, **({"poolclass": NullPool} if os.getenv("VERCEL") else {}))


def get_conn():
    """Dependência do FastAPI: abre uma ligação por pedido e fecha no fim."""
    with engine.connect() as conn:
        yield conn
