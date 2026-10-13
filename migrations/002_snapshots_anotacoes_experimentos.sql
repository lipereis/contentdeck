-- 002: métricas como capturas datadas, anotações por post e experimentos.

-- Dados que o export traz e o schema inicial não guardava
ALTER TABLE posts   ADD COLUMN IF NOT EXISTS duration_sec INT;
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS follows INT DEFAULT 0;

-- Anotações manuais: o CSV não diz o que foi testado em cada post
ALTER TABLE posts
    ADD COLUMN IF NOT EXISTS theme VARCHAR(50),        -- ex.: 'academia', 'nfl'
    ADD COLUMN IF NOT EXISTS hook TEXT,                -- o gancho dos primeiros segundos
    ADD COLUMN IF NOT EXISTS hashtag_set VARCHAR(50),  -- rótulo do conjunto usado, ex.: 'A'
    ADD COLUMN IF NOT EXISTS has_cta BOOLEAN,          -- a legenda pede uma ação?
    ADD COLUMN IF NOT EXISTS notes TEXT;

-- Uma captura por post por dia. As métricas do export são acumuladas ("Lifetime"),
-- então cada carga é uma fotografia; guardar a data permite ver a curva de cada post.
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS captured_on DATE;
UPDATE metrics SET captured_on = captured_at::date WHERE captured_on IS NULL;

-- Cargas repetidas no mesmo dia criavam linhas duplicadas: fica só a mais recente
DELETE FROM metrics a USING metrics b
 WHERE a.post_id = b.post_id AND a.captured_on = b.captured_on AND a.id < b.id;

ALTER TABLE metrics
    ALTER COLUMN captured_on SET NOT NULL,
    ALTER COLUMN captured_on SET DEFAULT CURRENT_DATE,
    ADD CONSTRAINT metrics_post_capture_uniq UNIQUE (post_id, captured_on);

-- Experimentos: uma hipótese, uma variável, posts divididos em variantes
CREATE TABLE experiments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    hypothesis TEXT,
    variable VARCHAR(100),      -- o que muda entre as variantes
    started_on DATE,
    ended_on DATE,
    result TEXT                 -- conclusão, preenchida no fim
);

CREATE TABLE experiment_posts (
    experiment_id INT REFERENCES experiments(id) ON DELETE CASCADE,
    post_id INT REFERENCES posts(id) ON DELETE CASCADE,
    variant VARCHAR(50) NOT NULL,   -- ex.: 'A', 'B', '15h', 'noite'
    PRIMARY KEY (experiment_id, post_id)
);

-- Captura mais recente de cada post: o que o painel mostra por padrão
CREATE VIEW latest_metrics AS
SELECT DISTINCT ON (post_id) *
  FROM metrics
 ORDER BY post_id, captured_on DESC, id DESC;
