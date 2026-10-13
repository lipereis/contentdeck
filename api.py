"""API do ContentDeck.

Correr:  uvicorn api:app --reload
Docs:    http://localhost:8000/docs

Todas as rotas de leitura usam latest_metrics (a captura mais recente de cada
post), exceto /posts/{id}/history, que devolve todas as capturas.
"""
import os
from datetime import date, datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Connection, text

from db import get_conn

# Na Vercel a API fica publicada sob /api; o prefixo é retirado antes de chegar aqui,
# e root_path faz a documentação (/api/docs) apontar para o sítio certo.
app = FastAPI(title="ContentDeck API", version="0.2.0", root_path="/api" if os.getenv("VERCEL") else "")

# Junção usada por quase todas as consultas: posts de um perfil com a captura mais recente
POSTS_LATEST = "FROM posts p JOIN latest_metrics m ON m.post_id = p.id WHERE p.profile_id = :pid"
MEDIANS = """percentile_cont(0.5) WITHIN GROUP (ORDER BY m.views)           AS median_views,
             percentile_cont(0.5) WITHIN GROUP (ORDER BY m.engagement_rate) AS median_engagement_rate"""


# ---------- modelos de resposta ----------

class Summary(BaseModel):
    handle: str
    platform: str
    posts: int
    captured_on: date | None          # data da captura mais recente
    views: int
    reach: int
    likes: int
    comments: int
    shares: int
    saves: int
    follows: int
    median_views: float | None
    median_engagement_rate: float | None   # fração: 0.05 = 5%
    top_post_share: float | None           # parte das views que vem do maior post


class Post(BaseModel):
    id: int
    url: str | None
    caption: str | None
    published_at: datetime
    duration_sec: int | None
    theme: str | None
    views: int
    reach: int
    likes: int
    comments: int
    shares: int
    saves: int
    follows: int
    engagement_rate: float


class Capture(BaseModel):
    captured_on: date
    views: int
    reach: int
    likes: int
    comments: int
    shares: int
    saves: int
    follows: int
    engagement_rate: float


class ThemeStats(BaseModel):
    theme: str | None
    posts: int
    median_views: float
    median_engagement_rate: float
    follows: int


class WeekStats(BaseModel):
    week_start: date
    posts: int
    views: int
    median_views: float
    median_engagement_rate: float


class Outlier(BaseModel):
    id: int
    url: str | None
    published_at: datetime
    views: int
    times_median: float     # quantas vezes a mediana do perfil
    share_of_views: float   # parte do total de views do perfil


class DurationBucket(BaseModel):
    bucket: str
    posts: int
    median_views: float
    median_engagement_rate: float


class Insights(BaseModel):
    posts: int
    median_views: float | None
    outlier_factor: float
    outliers: list[Outlier]
    follows_per_1000_reach: float | None
    likes_share_of_interactions: float | None   # 0.83 = 83% das interações são curtidas
    posts_without_comments: int
    posts_without_shares: int
    posts_without_saves: int
    posts_without_follows: int
    by_duration: list[DurationBucket]


class VariantStats(BaseModel):
    variant: str
    posts: int
    median_views: float
    median_engagement_rate: float
    follows: int


class Experiment(BaseModel):
    id: int
    name: str
    hypothesis: str | None
    variable: str | None
    started_on: date | None
    ended_on: date | None
    result: str | None
    variants: list[VariantStats]


class Deck(BaseModel):
    summary: Summary
    posts: list[Post]
    themes: list[ThemeStats]
    weekly: list[WeekStats]
    insights: Insights
    experiments: list[Experiment]


# ---------- apoio ----------

def profile_id(conn: Connection, handle: str, platform: str) -> int:
    """ID do perfil, ou 404 se não existir."""
    row = conn.execute(
        text("SELECT id FROM profiles WHERE handle = :h AND platform = :p"),
        {"h": handle, "p": platform},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Perfil @{handle} ({platform}) não encontrado")
    return row[0]


def rows(conn: Connection, sql: str, **params) -> list[dict]:
    return [dict(r) for r in conn.execute(text(sql), params).mappings()]


# ---------- rotas ----------

@app.get("/health")
def health(conn: Connection = Depends(get_conn)):
    conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/profiles/{handle}/summary", response_model=Summary)
def summary(handle: str, platform: str = "instagram", conn: Connection = Depends(get_conn)):
    """Números gerais do perfil. Mediana em vez de média: um post viral distorce a média."""
    pid = profile_id(conn, handle, platform)
    row = rows(conn, f"""
        SELECT count(*)                     AS posts,
               max(m.captured_on)           AS captured_on,
               coalesce(sum(m.views), 0)    AS views,
               coalesce(sum(m.reach), 0)    AS reach,
               coalesce(sum(m.likes), 0)    AS likes,
               coalesce(sum(m.comments), 0) AS comments,
               coalesce(sum(m.shares), 0)   AS shares,
               coalesce(sum(m.saves), 0)    AS saves,
               coalesce(sum(m.follows), 0)  AS follows,
               {MEDIANS},
               max(m.views)                 AS top_views
          {POSTS_LATEST}
    """, pid=pid)[0]
    top_views = row.pop("top_views")
    share = top_views / row["views"] if row["views"] else None
    return Summary(handle=handle, platform=platform, top_post_share=share, **row)


# Nome de coluna e direção não podem ser parâmetros SQL (:x). A tradução por
# dicionário garante que só texto escrito aqui chega à consulta.
SORT_COLUMNS = {"published": "p.published_at", "views": "m.views", "engagement": "m.engagement_rate"}


@app.get("/profiles/{handle}/posts", response_model=list[Post])
def list_posts(
    handle: str,
    platform: str = "instagram",
    sort: str = Query("published", pattern="^(published|views|engagement)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    theme: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    conn: Connection = Depends(get_conn),
):
    """Posts do perfil com a captura mais recente, ordenados e opcionalmente filtrados por tema."""
    pid = profile_id(conn, handle, platform)
    direction = "ASC" if order == "asc" else "DESC"
    return rows(conn, f"""
        SELECT p.id, p.url, p.caption, p.published_at, p.duration_sec, p.theme,
               m.views, m.reach, m.likes, m.comments, m.shares, m.saves, m.follows, m.engagement_rate
          {POSTS_LATEST}
           AND (CAST(:theme AS text) IS NULL OR p.theme = :theme)
         ORDER BY {SORT_COLUMNS[sort]} {direction}, p.id
         LIMIT :limit
    """, pid=pid, theme=theme, limit=limit)


@app.get("/posts/{post_id}/history", response_model=list[Capture])
def post_history(post_id: int, conn: Connection = Depends(get_conn)):
    """Todas as capturas de um post, da mais antiga para a mais recente: a curva de crescimento."""
    history = rows(conn, """
        SELECT captured_on, views, reach, likes, comments, shares, saves, follows, engagement_rate
          FROM metrics WHERE post_id = :id ORDER BY captured_on
    """, id=post_id)
    if not history:
        raise HTTPException(status_code=404, detail=f"Post {post_id} não encontrado")
    return history


@app.get("/profiles/{handle}/themes", response_model=list[ThemeStats])
def themes(handle: str, platform: str = "instagram", conn: Connection = Depends(get_conn)):
    """Comparação por tema anotado. Posts sem tema ficam agrupados com theme = null."""
    pid = profile_id(conn, handle, platform)
    return rows(conn, f"""
        SELECT p.theme, count(*) AS posts, {MEDIANS}, coalesce(sum(m.follows), 0) AS follows
          {POSTS_LATEST}
         GROUP BY p.theme
         ORDER BY count(*) DESC, p.theme
    """, pid=pid)


@app.get("/profiles/{handle}/weekly", response_model=list[WeekStats])
def weekly(handle: str, platform: str = "instagram", conn: Connection = Depends(get_conn)):
    """Evolução por semana de publicação (segunda-feira como início)."""
    pid = profile_id(conn, handle, platform)
    return rows(conn, f"""
        SELECT date_trunc('week', p.published_at)::date AS week_start,
               count(*) AS posts, sum(m.views) AS views, {MEDIANS}
          {POSTS_LATEST}
         GROUP BY 1
         ORDER BY 1
    """, pid=pid)


@app.get("/profiles/{handle}/insights", response_model=Insights)
def insights(
    handle: str,
    platform: str = "instagram",
    outlier_factor: float = Query(3.0, ge=1.0, description="Um post é fora da curva se tiver mais que N vezes a mediana de views"),
    conn: Connection = Depends(get_conn),
):
    """Leituras prontas sobre o perfil: posts fora da curva, conversão em seguidores,
    composição das interações e desempenho por duração."""
    pid = profile_id(conn, handle, platform)
    totals = rows(conn, f"""
        SELECT count(*) AS posts,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY m.views) AS median_views,
               coalesce(sum(m.views), 0) AS views, coalesce(sum(m.reach), 0) AS reach,
               coalesce(sum(m.follows), 0) AS follows, coalesce(sum(m.likes), 0) AS likes,
               coalesce(sum(m.likes + m.comments + m.shares + m.saves), 0) AS interactions,
               count(*) FILTER (WHERE m.comments = 0) AS posts_without_comments,
               count(*) FILTER (WHERE m.shares = 0)   AS posts_without_shares,
               count(*) FILTER (WHERE m.saves = 0)    AS posts_without_saves,
               count(*) FILTER (WHERE m.follows = 0)  AS posts_without_follows
          {POSTS_LATEST}
    """, pid=pid)[0]

    outliers = []
    if totals["median_views"]:
        outliers = rows(conn, f"""
            SELECT p.id, p.url, p.published_at, m.views,
                   m.views / :median           AS times_median,
                   m.views::float / :total     AS share_of_views
              {POSTS_LATEST} AND m.views > :median * :factor
             ORDER BY m.views DESC
        """, pid=pid, median=totals["median_views"], total=totals["views"], factor=outlier_factor)

    by_duration = rows(conn, f"""
        SELECT CASE WHEN p.duration_sec <= 20 THEN 'até 20 s'
                    WHEN p.duration_sec <= 60 THEN '21–60 s'
                    ELSE 'mais de 60 s' END AS bucket,
               count(*) AS posts, {MEDIANS}
          {POSTS_LATEST} AND p.duration_sec IS NOT NULL
         GROUP BY 1
         ORDER BY min(p.duration_sec)
    """, pid=pid)

    return Insights(
        posts=totals["posts"],
        median_views=totals["median_views"],
        outlier_factor=outlier_factor,
        outliers=outliers,
        follows_per_1000_reach=totals["follows"] / totals["reach"] * 1000 if totals["reach"] else None,
        likes_share_of_interactions=totals["likes"] / totals["interactions"] if totals["interactions"] else None,
        posts_without_comments=totals["posts_without_comments"],
        posts_without_shares=totals["posts_without_shares"],
        posts_without_saves=totals["posts_without_saves"],
        posts_without_follows=totals["posts_without_follows"],
        by_duration=by_duration,
    )


@app.get("/profiles/{handle}/experiments", response_model=list[Experiment])
def experiments(handle: str, platform: str = "instagram", conn: Connection = Depends(get_conn)):
    """Experimentos com posts deste perfil e o desempenho de cada variante.

    A API só descreve cada variante; não declara vencedor. Com poucos posts por
    variante a diferença costuma ser ruído, e essa leitura fica com quem analisa.
    """
    pid = profile_id(conn, handle, platform)
    stats = rows(conn, f"""
        SELECT e.id, e.name, e.hypothesis, e.variable, e.started_on, e.ended_on, e.result,
               ep.variant, count(*) AS posts, {MEDIANS}, coalesce(sum(m.follows), 0) AS follows
          FROM experiments e
          JOIN experiment_posts ep ON ep.experiment_id = e.id
          JOIN posts p ON p.id = ep.post_id
          JOIN latest_metrics m ON m.post_id = p.id
         WHERE p.profile_id = :pid
         GROUP BY e.id, ep.variant
         ORDER BY e.id, ep.variant
    """, pid=pid)

    result: dict[int, Experiment] = {}
    for s in stats:
        exp = result.setdefault(s["id"], Experiment(
            **{k: s[k] for k in ("id", "name", "hypothesis", "variable", "started_on", "ended_on", "result")},
            variants=[]))
        exp.variants.append(VariantStats(
            **{k: s[k] for k in ("variant", "posts", "median_views", "median_engagement_rate", "follows")}))
    return list(result.values())


@app.get("/profiles/{handle}/deck", response_model=Deck)
def deck(handle: str, platform: str = "instagram", conn: Connection = Depends(get_conn)):
    """Tudo o que o painel mostra, num pedido só e numa única ligação à base.

    O painel pedia seis rotas em paralelo; em serverless isso eram seis funções e
    seis ligações novas por visita. As rotas individuais continuam a existir.
    """
    return Deck(
        summary=summary(handle, platform, conn),
        posts=list_posts(handle, platform, sort="published", order="asc", theme=None, limit=200, conn=conn),
        themes=themes(handle, platform, conn),
        weekly=weekly(handle, platform, conn),
        insights=insights(handle, platform, outlier_factor=3.0, conn=conn),
        experiments=experiments(handle, platform, conn),
    )
