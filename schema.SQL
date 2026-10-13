-- Tabela de Perfis
CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL, -- 'instagram', 'tiktok'
    handle VARCHAR(100) NOT NULL,
    UNIQUE (platform, handle)
);

-- Tabela Central de Posts
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    profile_id INT REFERENCES profiles(id) ON DELETE CASCADE,
    external_id VARCHAR(100) UNIQUE NOT NULL,
    caption TEXT,
    media_type VARCHAR(50) DEFAULT 'post',
    url TEXT,
    published_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Métricas
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    post_id INT REFERENCES posts(id) ON DELETE CASCADE,
    reach INT DEFAULT 0,
    views INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    saves INT DEFAULT 0,
    engagement_rate NUMERIC(6,4) DEFAULT 0.0000,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);