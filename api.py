"""API do ContentDeck.

Correr:  uvicorn api:app --reload
Docs:    http://localhost:8000/docs

A rota /summary está completa e serve de modelo. As três rotas marcadas com
EXERCÍCIO devolvem 501 até serem implementadas; os testes delas estão em
tests/test_exercicios.py.
"""
from datetime import date, datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Connection, text

from db import get_conn

app = FastAPI(title="ContentDeck API", version="0.1.0")


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


# ---------- rotas ----------

@app.get("/health")
def health(conn: Connection = Depends(get_conn)):
    conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/profiles/{handle}/summary", response_model=Summary)
def summary(handle: str, platform: str = "instagram", conn: Connection = Depends(get_conn)):
    """Números gerais do perfil, usando a captura mais recente de cada post.

    MODELO para as outras rotas. Repare em três coisas:
    1. os valores do utilizador entram como parâmetros (:pid), nunca colados na string SQL;
    2. a consulta lê de latest_metrics, não de metrics, para não somar capturas antigas;
    3. mediana em vez de média: um post viral distorce a média.
    """
    pid = profile_id(conn, handle, platform)
    row = conn.execute(text("""
        SELECT count(*)                         AS posts,
               max(m.captured_on)               AS captured_on,
               coalesce(sum(m.views), 0)        AS views,
               coalesce(sum(m.reach), 0)        AS reach,
               coalesce(sum(m.likes), 0)        AS likes,
               coalesce(sum(m.comments), 0)     AS comments,
               coalesce(sum(m.shares), 0)       AS shares,
               coalesce(sum(m.saves), 0)        AS saves,
               coalesce(sum(m.follows), 0)      AS follows,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY m.views)           AS median_views,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY m.engagement_rate) AS median_engagement_rate,
               max(m.views)                     AS top_views
          FROM posts p
          JOIN latest_metrics m ON m.post_id = p.id
         WHERE p.profile_id = :pid
    """), {"pid": pid}).mappings().one()

    share = row["top_views"] / row["views"] if row["views"] else None
    return Summary(handle=handle, platform=platform, top_post_share=share,
                   **{k: v for k, v in row.items() if k != "top_views"})


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
    """EXERCÍCIO 1 — lista de posts com a captura mais recente.

    - `sort` escolhe a coluna: published -> p.published_at, views -> m.views,
      engagement -> m.engagement_rate. `order` é asc ou desc.
    - `theme`, se vier, filtra por p.theme.
    - `limit` corta o resultado.

    Cuidado: nomes de coluna e ASC/DESC NÃO podem ser parâmetros (:x) em SQL.
    Use um dicionário que traduz o valor de `sort` para a coluna certa; nunca
    cole texto do utilizador na consulta. O `pattern` acima já rejeita valores
    fora da lista, mas o dicionário é a segunda barreira.
    """
    raise HTTPException(status_code=501, detail="Exercício 1 por implementar")


@app.get("/profiles/{handle}/themes", response_model=list[ThemeStats])
def themes(handle: str, platform: str = "instagram", conn: Connection = Depends(get_conn)):
    """EXERCÍCIO 2 — comparação por tema.

    Uma linha por p.theme (posts sem tema ficam com theme = null), com número de
    posts, mediana de views, mediana de engagement_rate e soma de follows.
    Ordene por número de posts, do maior para o menor.
    Dica: é um GROUP BY sobre a mesma junção da rota /summary.
    """
    raise HTTPException(status_code=501, detail="Exercício 2 por implementar")


@app.get("/profiles/{handle}/weekly", response_model=list[WeekStats])
def weekly(handle: str, platform: str = "instagram", conn: Connection = Depends(get_conn)):
    """EXERCÍCIO 3 — evolução por semana de publicação.

    Uma linha por semana (segunda-feira como início), em ordem cronológica, com
    número de posts, soma de views, mediana de views e mediana de engagement_rate.
    Dica: date_trunc('week', p.published_at)::date dá a segunda-feira da semana.
    """
    raise HTTPException(status_code=501, detail="Exercício 3 por implementar")
