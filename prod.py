"""Corre um script do projeto contra a base publicada (Neon, via Vercel).

Uso:
  vercel env pull .env.vercel --environment=production --yes   # uma vez, ou quando a base mudar
  python prod.py migrate.py
  python prod.py ingest.py
  python prod.py annotate.py load

O URL da base nunca é mostrado. O .env.vercel fica fora do git.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE / ".env.vercel"
# Ligação direta (sem pooler): mais segura para migrações e cargas.
KEYS = ("DATABASE_URL_UNPOOLED", "DATABASE_URL")


def production_url() -> str:
    if not ENV_FILE.exists():
        sys.exit("Falta o .env.vercel. Rode: vercel env pull .env.vercel --environment=production --yes")
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    for key in KEYS:
        if values.get(key):
            return values[key]
    sys.exit("O .env.vercel não tem DATABASE_URL.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    env = {**os.environ, "DATABASE_URL": production_url(), "PYTHONIOENCODING": "utf-8"}
    print("A correr contra a base PUBLICADA.", flush=True)
    sys.exit(subprocess.call([sys.executable, *sys.argv[1:]], env=env, cwd=HERE))
