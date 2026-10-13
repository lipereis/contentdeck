import glob
import os
import re
from datetime import date

import pandas as pd
from sqlalchemy import text

# Ligação única do projeto (lê o .env e normaliza o URL da base)
from db import engine

MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}

def capture_date(file_path: str) -> date:
    """
    Data da captura das métricas. O export da Meta chama-se
    'Sep-15-2026_Oct-12-2026_<id>.csv': a segunda data é o fim do período,
    ou seja, o dia a que os números acumulados se referem. Sem esse padrão, usa hoje.
    """
    found = re.findall(r"([A-Z][a-z]{2})-(\d{2})-(\d{4})", os.path.basename(file_path))
    if len(found) >= 2 and found[1][0] in MONTHS:
        month, day, year = found[1]
        return date(int(year), MONTHS[month], int(day))
    return date.today()

def latest_export(folder: str = "data"):
    """CSV mais recente da pasta, ignorando os exemplos (*_export.csv) e as anotações."""
    files = [f for f in glob.glob(os.path.join(folder, "*.csv"))
             if not f.endswith("_export.csv") and os.path.basename(f) != "annotations.csv"]
    return max(files, key=os.path.getmtime) if files else None

def normalize_instagram_df(df):
    """
    Mapeia e limpa os campos exportados do Instagram Insights (Meta Business Suite).
    """
    normalized = pd.DataFrame()
    
    normalized['external_id'] = df['Post ID'].astype(str)
    # Converte o timestamp vindo do relatório do Instagram
    # O export usa mês/dia/ano ('10/09/2026 15:10' é 9 de outubro)
    normalized['published_at'] = pd.to_datetime(df['Publish time'], format='%m/%d/%Y %H:%M', errors='coerce')
    normalized['caption'] = df.get('Description', '').fillna('')
    normalized['media_type'] = df.get('Post type', 'post').fillna('post')
    normalized['url'] = df.get('Permalink', '').fillna('')
    normalized['duration_sec'] = pd.to_numeric(df.get('Duration (sec)'), errors='coerce').astype('Int64')

    # Métricas numéricas brutas
    normalized['reach'] = pd.to_numeric(df['Reach'], errors='coerce').fillna(0).astype(int)
    normalized['views'] = pd.to_numeric(df['Views'], errors='coerce').fillna(0).astype(int)
    normalized['likes'] = pd.to_numeric(df['Likes'], errors='coerce').fillna(0).astype(int)
    normalized['comments'] = pd.to_numeric(df['Comments'], errors='coerce').fillna(0).astype(int)
    normalized['shares'] = pd.to_numeric(df['Shares'], errors='coerce').fillna(0).astype(int)
    normalized['saves'] = pd.to_numeric(df['Saves'], errors='coerce').fillna(0).astype(int)
    normalized['follows'] = pd.to_numeric(df.get('Follows', 0), errors='coerce').fillna(0).astype(int)

    return normalized

def process_csv(file_path: str, platform: str, profile_handle: str, captured_on: date | None = None):
    captured_on = captured_on or capture_date(file_path)
    print(f"🔄 A processar o CSV do {platform.upper()} para @{profile_handle} (captura de {captured_on})...")
    df = pd.read_csv(file_path)
    
    if platform.lower() == 'instagram':
        normalized = normalize_instagram_df(df)
    elif platform.lower() == 'tiktok':
        # Estrutura para quando exportares o TikTok futuramente
        normalized = pd.DataFrame()
        normalized['external_id'] = df['Video ID'].astype(str)
        normalized['published_at'] = pd.to_datetime(df['Posting time'], errors='coerce')
        normalized['caption'] = df.get('Video caption', '').fillna('')
        normalized['media_type'] = 'video'
        normalized['url'] = df.get('Video link', '').fillna('')
        normalized['reach'] = pd.to_numeric(df['Video views'], errors='coerce').fillna(0).astype(int)
        normalized['views'] = pd.to_numeric(df['Video views'], errors='coerce').fillna(0).astype(int)
        normalized['likes'] = pd.to_numeric(df['Likes'], errors='coerce').fillna(0).astype(int)
        normalized['comments'] = pd.to_numeric(df['Comments'], errors='coerce').fillna(0).astype(int)
        normalized['shares'] = pd.to_numeric(df['Shares'], errors='coerce').fillna(0).astype(int)
        normalized['saves'] = 0
        normalized['follows'] = 0
        normalized['duration_sec'] = pd.array([pd.NA] * len(df), dtype='Int64')
    else:
        raise ValueError("Plataforma desconhecida.")

    # Cálculo da Taxa de Engajamento: (Curtidas + Comentários + Shares + Saves) / Alcance
    total_interactions = normalized['likes'] + normalized['comments'] + normalized['shares'] + normalized['saves']
    normalized['engagement_rate'] = (total_interactions / normalized['reach'].replace(0, 1)).round(4)

    # Persistência no Postgres
    with engine.begin() as conn:
        # 1. Cria ou obtém o ID do perfil
        res = conn.execute(
            text("""
                INSERT INTO profiles (platform, handle) 
                VALUES (:platform, :handle) 
                ON CONFLICT (platform, handle) DO UPDATE SET handle = EXCLUDED.handle
                RETURNING id;
            """), 
            {"platform": platform, "handle": profile_handle}
        )
        profile_id = res.fetchone()[0]

        # 2. Insere posts e respetivas métricas
        for _, row in normalized.iterrows():
            post_res = conn.execute(
                text("""
                    INSERT INTO posts (profile_id, external_id, published_at, caption, media_type, url, duration_sec)
                    VALUES (:profile_id, :external_id, :published_at, :caption, :media_type, :url, :duration_sec)
                    ON CONFLICT (external_id) DO UPDATE
                    SET caption = EXCLUDED.caption, url = EXCLUDED.url, duration_sec = EXCLUDED.duration_sec
                    RETURNING id;
                """),
                {
                    "profile_id": profile_id,
                    "external_id": row['external_id'],
                    "published_at": row['published_at'],
                    "caption": row['caption'],
                    "media_type": row['media_type'],
                    "url": row['url'],
                    "duration_sec": None if pd.isna(row['duration_sec']) else int(row['duration_sec'])
                }
            )
            post_id = post_res.fetchone()[0]

            # Uma captura por post por dia: recarregar o mesmo export atualiza, não duplica
            conn.execute(
                text("""
                    INSERT INTO metrics (post_id, captured_on, reach, views, likes, comments, shares, saves, follows, engagement_rate)
                    VALUES (:post_id, :captured_on, :reach, :views, :likes, :comments, :shares, :saves, :follows, :engagement_rate)
                    ON CONFLICT (post_id, captured_on) DO UPDATE
                    SET reach = EXCLUDED.reach, views = EXCLUDED.views, likes = EXCLUDED.likes,
                        comments = EXCLUDED.comments, shares = EXCLUDED.shares, saves = EXCLUDED.saves,
                        follows = EXCLUDED.follows, engagement_rate = EXCLUDED.engagement_rate,
                        captured_at = CURRENT_TIMESTAMP;
                """),
                {
                    "post_id": post_id,
                    "captured_on": captured_on,
                    "reach": int(row['reach']),
                    "views": int(row['views']),
                    "likes": int(row['likes']),
                    "comments": int(row['comments']),
                    "shares": int(row['shares']),
                    "saves": int(row['saves']),
                    "follows": int(row['follows']),
                    "engagement_rate": float(row['engagement_rate'])
                }
            )

    print(f"✅ Sucesso! {len(normalized)} posts carregados para @{profile_handle} ({platform}), captura de {captured_on}.")

if __name__ == "__main__":
    # Uso: python ingest.py [ficheiro.csv] [plataforma] [handle]
    # Sem ficheiro, usa o export mais recente da pasta data/.
    import sys

    csv_file = sys.argv[1] if len(sys.argv) > 1 else latest_export()
    platform = sys.argv[2] if len(sys.argv) > 2 else "instagram"
    handle = sys.argv[3] if len(sys.argv) > 3 else "insidereismind"

    if csv_file and os.path.exists(csv_file):
        process_csv(csv_file, platform=platform, profile_handle=handle)
    else:
        print(f"⚠️ Ficheiro {csv_file or 'de export'} não encontrado em data/!")