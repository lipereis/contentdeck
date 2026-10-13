# ContentDeck

Métricas de conteúdo sem chute: carrega exports do Instagram num Postgres, guarda a evolução de cada post e serve leituras prontas por uma API. Construído para rodar experimentos de publicação num perfil real, [@insidereismind](https://www.instagram.com/insidereismind/).

**Estado:** carga, schema com histórico, anotações, experimentos e API prontos e testados. Faltam o painel web e o deploy.

## Por que existe

O Instagram mostra números por post, mas não responde "postar à noite rende mais?" nem "esse vídeo foi bom ou só teve mais tempo no ar?". O ContentDeck guarda cada export como uma captura datada, deixa anotar o que foi testado em cada post e compara grupos com mediana, porque um único post viral distorce qualquer média.

Primeiro export real (18 Reels, 22 dias): mediana de 128 visualizações por post, um post fora da curva com 41% do total, 2 seguidores ganhos. É o ponto de partida dos experimentos.

## API

`uvicorn api:app --reload`, documentação interativa em `http://localhost:8000/docs`.

| Rota | Devolve |
|---|---|
| `GET /profiles/{handle}/summary` | totais, medianas e peso do maior post |
| `GET /profiles/{handle}/posts` | posts ordenáveis por data, views ou engajamento; filtro por tema |
| `GET /posts/{id}/history` | todas as capturas de um post: a curva de crescimento |
| `GET /profiles/{handle}/themes` | comparação por tema anotado |
| `GET /profiles/{handle}/weekly` | evolução por semana de publicação |
| `GET /profiles/{handle}/insights` | posts fora da curva, seguidores por mil de alcance, composição das interações, desempenho por duração |
| `GET /profiles/{handle}/experiments` | cada experimento com o desempenho por variante |

A rota de experimentos descreve as variantes e não declara vencedor: com poucos posts por grupo a diferença costuma ser ruído.

## Como rodar

Requer Python 3.13 e PostgreSQL local, com uma base de dados já criada.

```bash
python -m venv .venv
source .venv/Scripts/activate        # Git Bash no Windows; no Linux/macOS: .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # ajuste utilizador, senha e base
python migrate.py                    # cria as tabelas
python ingest.py data/instagram_export.csv instagram exemplo
uvicorn api:app --reload
```

Depois abra `http://localhost:8000/profiles/exemplo/summary`.

## Rotina semanal

1. Exportar os posts no Meta Business Suite e guardar o CSV em `data/`, com o nome original.
2. `python ingest.py` carrega o export mais recente. A data da captura sai do nome do ficheiro.
3. `python annotate.py template`, preencher `data/annotations.csv`, `python annotate.py load`.

Carregar o mesmo export duas vezes atualiza, não duplica.

## Modelo de dados

```
profiles ─< posts ─< metrics            uma linha de metrics por post por dia de captura
              └──< experiment_posts >── experiments
```

- **Capturas datadas.** As métricas do export são acumuladas, então cada carga é uma fotografia (`captured_on`), única por post e dia.
- **`latest_metrics`.** Visão com a captura mais recente de cada post; as rotas leem daqui para não somar capturas antigas.
- **Anotações.** Tema, gancho, conjunto de hashtags e chamada para ação ficam em `posts`, preenchidos à mão: o export não diz o que foi testado.
- **Migrações.** `schema.SQL` é a versão 001; `migrate.py` aplica cada ficheiro de `migrations/` uma única vez, dentro de uma transação.

## Estrutura

| Ficheiro | Função |
|---|---|
| `schema.SQL`, `migrations/`, `migrate.py` | schema versionado |
| `ingest.py` | lê o CSV, normaliza e grava posts e métricas |
| `annotate.py` | anotações manuais e ligação a experimentos |
| `analyze.py` | análise exploratória de um export, no terminal |
| `db.py`, `api.py` | API em FastAPI |
| `tests/` | 25 testes, numa base própria criada e apagada a cada execução |

## Testes

```bash
pytest tests
```

Os testes criam `contentdeck_test`, aplicam as migrações, carregam o CSV de exemplo e apagam a base no fim. A base real não é tocada. Correm também no GitHub Actions, com Postgres 17.

## Limitações conhecidas

- O caminho do TikTok em `ingest.py` nunca foi testado com um export real.
- `posts.external_id` é único no banco inteiro, não por perfil.
- Sem dados de retenção (tempo assistido): o export usado não os traz.
- Comparar posts de idades diferentes ainda é injusto; "views nos primeiros 7 dias" depende de acumular mais capturas.
- A API é só de leitura e não tem autenticação; a carga é feita pela linha de comandos.

## Licença

MIT.
