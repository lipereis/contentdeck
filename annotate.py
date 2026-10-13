"""Anotações manuais dos posts e ligação a experimentos.

O export não diz o que foi testado em cada post. Este script cria uma folha
para preencher à mão e depois grava o que foi preenchido.

Uso:
  python annotate.py template   # cria/atualiza data/annotations.csv (não apaga o já preenchido)
  python annotate.py load       # grava as anotações no banco

Colunas a preencher: theme, hook, hashtag_set, has_cta (sim/não), notes,
experiment (nome do experimento) e variant (ex.: A, B, 15h, noite).
A chave é o link do post: IDs numéricos longos são corrompidos por folhas de cálculo.
"""
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

HERE = Path(__file__).resolve().parent
FILE = HERE / "data" / "annotations.csv"
FIELDS = ["theme", "hook", "hashtag_set", "has_cta", "notes"]
TRUE = {"sim", "s", "yes", "y", "true", "1", "x"}
FALSE = {"não", "nao", "n", "no", "false", "0"}

load_dotenv(HERE / ".env")
engine = create_engine(os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/contentdeck"))


def template():
    df = pd.read_sql("""
        SELECT p.url, to_char(p.published_at, 'DD/MM HH24"h"') AS publicado, p.duration_sec AS duracao,
               left(p.caption, 60) AS legenda, p.theme, p.hook, p.hashtag_set,
               CASE WHEN p.has_cta THEN 'sim' WHEN p.has_cta = false THEN 'não' END AS has_cta,
               p.notes, e.name AS experiment, ep.variant
          FROM posts p
          LEFT JOIN experiment_posts ep ON ep.post_id = p.id
          LEFT JOIN experiments e ON e.id = ep.experiment_id
         ORDER BY p.published_at
    """, engine)
    df.to_csv(FILE, index=False, encoding="utf-8-sig")
    print(f"{len(df)} posts em {FILE.relative_to(HERE)}. Preencha e rode: python annotate.py load")


def load():
    df = pd.read_csv(FILE, dtype=str, encoding="utf-8-sig").fillna("")
    updated = linked = 0
    with engine.begin() as conn:
        for _, r in df.iterrows():
            flag = r["has_cta"].strip().lower()
            if flag and flag not in TRUE | FALSE:
                raise ValueError(f"has_cta inválido em {r['url']}: {r['has_cta']!r} (use sim ou não)")
            values = {f: (r[f].strip() or None) for f in FIELDS if f != "has_cta"}
            values["has_cta"] = True if flag in TRUE else False if flag in FALSE else None
            res = conn.execute(text("""
                UPDATE posts SET theme = :theme, hook = :hook, hashtag_set = :hashtag_set,
                                 has_cta = :has_cta, notes = :notes
                 WHERE url = :url RETURNING id
            """), {**values, "url": r["url"]}).fetchone()
            if res is None:
                print(f"  aviso: post não encontrado no banco: {r['url']}")
                continue
            updated += 1

            name, variant = r["experiment"].strip(), r["variant"].strip()
            if bool(name) != bool(variant):
                raise ValueError(f"{r['url']}: experiment e variant têm de vir juntos")
            if name:
                exp_id = conn.execute(text("""
                    INSERT INTO experiments (name) VALUES (:n)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id
                """), {"n": name}).fetchone()[0]
                conn.execute(text("""
                    INSERT INTO experiment_posts (experiment_id, post_id, variant) VALUES (:e, :p, :v)
                    ON CONFLICT (experiment_id, post_id) DO UPDATE SET variant = EXCLUDED.variant
                """), {"e": exp_id, "p": res[0], "v": variant})
                linked += 1
    print(f"{updated} posts anotados, {linked} ligados a experimentos.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "template":
        template()
    elif cmd == "load":
        load()
    else:
        print(__doc__)
