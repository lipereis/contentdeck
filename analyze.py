"""Análise exploratória de um export do Instagram (Meta Business Suite).

Uso: python analyze.py [ficheiro.csv]
Lê o CSV diretamente (inclui Duration e Follows, que o schema ainda não guarda)
e confere a contagem com o que está no Postgres.
"""
import os
import re
import sys

import pandas as pd

from db import engine
from ingest import latest_export

CSV = sys.argv[1] if len(sys.argv) > 1 else latest_export()
FAIXAS = dict(bins=[0, 20, 60, 600], labels=["até 20 s", "21–60 s", "mais de 60 s"])
ARTISTAS = "deftones|staind|post malone|tame impala|frank ocean|música"

pd.set_option("display.width", 200)

df = pd.read_csv(CSV)
df["quando"] = pd.to_datetime(df["Publish time"], format="%m/%d/%Y %H:%M")
df = df.sort_values("quando").reset_index(drop=True)
df["inter"] = df[["Likes", "Comments", "Shares", "Saves"]].sum(axis=1)
df["eng"] = df["inter"] / df["Reach"] * 100
df["dur"] = df["Duration (sec)"]
df["faixa"] = pd.cut(df["dur"], **FAIXAS)

try:
    db = pd.read_sql("select (select count(*) from posts) posts, (select count(*) from metrics) metricas", engine)
    print("BANCO:", db.to_dict("records")[0], "| CSV:", len(df), "linhas")
except Exception as e:  # análise funciona sem banco
    print("BANCO indisponível:", type(e).__name__)

print("\nTIPOS:", df["Post type"].value_counts().to_dict(), "| período", df.quando.min(), "->", df.quando.max())
print("TOTAIS:", df[["Views", "Reach", "Likes", "Comments", "Shares", "Saves", "Follows", "inter"]].sum().to_dict())
for c in ["Views", "Reach", "inter", "eng", "dur"]:
    s = df[c]
    print(f"  {c:6} média {s.mean():7.1f}  mediana {s.median():7.1f}  mín {s.min():6.1f}  máx {s.max():7.1f}")

top = df.loc[df.Views.idxmax()]
rest = df.drop(df.Views.idxmax())
print(f"\nMAIOR POST: {top.quando:%d/%m} com {top.Views} views = {top.Views / df.Views.sum() * 100:.0f}% do total, "
      f"{top.Views / rest.Views.median():.1f}x a mediana dos outros; {top.dur} s; engajamento {top.eng:.1f}%")
for nome, d in (("TODOS", df), ("SEM O MAIOR", rest)):
    print(f"{nome:12} views média {d.Views.mean():.0f} mediana {d.Views.median():.0f} | "
          f"eng médio {d.eng.mean():.2f}% mediana {d.eng.median():.2f}% agregado {d.inter.sum() / d.Reach.sum() * 100:.2f}%")

print("\nPOR POST:")
print(df.assign(dia=df.quando.dt.strftime("%d/%m %a %Hh"))[
    ["dia", "dur", "Views", "Reach", "Likes", "Comments", "Shares", "Saves", "Follows", "eng"]].round(1).to_string(index=False))

agg = dict(n=("Views", "size"), views_mediana=("Views", "median"), views_media=("Views", "mean"), eng_mediana=("eng", "median"))
print("\nPOR DURAÇÃO (todos):")
print(df.groupby("faixa", observed=True).agg(**agg).round(1))
print("POR DURAÇÃO (sem o maior):")
print(rest.groupby("faixa", observed=True).agg(**agg).round(1))
print(f"correlação duração x views (sem o maior): pearson {rest.dur.corr(rest.Views):.2f}, "
      f"spearman {rest.dur.rank().corr(rest.Views.rank()):.2f}")

df["semana"] = df.quando.dt.isocalendar().week
print("\nPOR SEMANA:")
print(df.groupby("semana").agg(inicio=("quando", "min"), n=("Views", "size"), views=("Views", "sum"),
                               views_mediana=("Views", "median"), eng_mediana=("eng", "median")).round({"eng_mediana": 1}))

print("\nHORA DE PUBLICAÇÃO:", df.quando.dt.hour.value_counts().sort_index().to_dict())
print(f"VIEWS / ALCANCE: {df.Views.sum() / df.Reach.sum():.2f}")

tags: dict[str, list[int]] = {}
for _, r in df.iterrows():
    for t in set(re.findall(r"#(\w+)", r.Description.lower())):
        tags.setdefault(t, []).append(r.Views)
print("\nHASHTAGS (n, mediana de views):",
      {t: (len(v), int(pd.Series(v).median())) for t, v in sorted(tags.items(), key=lambda x: -len(x[1]))})

df["cita_musica"] = df.Description.str.contains(ARTISTAS, case=False)
print("LEGENDA CITA MÚSICA/ARTISTA:")
print(df.groupby("cita_musica").agg(n=("Views", "size"), views_mediana=("Views", "median"), eng_mediana=("eng", "median")).round({"eng_mediana": 1}))

n = len(df)
print(f"\nPOSTS COM ZERO: comentários {(df.Comments == 0).sum()}/{n}, compartilhamentos {(df.Shares == 0).sum()}/{n}, "
      f"salvamentos {(df.Saves == 0).sum()}/{n}, seguidores ganhos {(df.Follows == 0).sum()}/{n}")
