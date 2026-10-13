# ContentDeck

Painel de métricas de conteúdo: carrega exports do Instagram num Postgres, guarda a evolução de cada post e serve os números por uma API. Usado para rodar experimentos de publicação no perfil @insidereismind.

Em construção. Feito: carga, schema com histórico, anotações, primeira rota da API. Falta: resto da API, painel web, deploy.

## Como rodar

Requer Python 3.13 e PostgreSQL a correr localmente.

```bash
python -m venv .venv
source .venv/Scripts/activate        # Git Bash no Windows
pip install -r requirements.txt
cp .env.example .env                 # ajuste utilizador e senha
python migrate.py                    # cria as tabelas (a base de dados tem de existir)
python ingest.py data/instagram_export.csv instagram exemplo
uvicorn api:app --reload             # http://localhost:8000/docs
```

## Rotina semanal

1. Exportar os posts no Meta Business Suite e guardar o CSV em `data/`, com o nome original.
2. `python ingest.py` — carrega o export mais recente. A data da captura sai do nome do ficheiro.
3. `python annotate.py template`, preencher `data/annotations.csv`, `python annotate.py load`.

Carregar o mesmo export duas vezes atualiza, não duplica.

## Estrutura

| Ficheiro | Função |
|---|---|
| `schema.SQL`, `migrations/` | tabelas; `migrate.py` aplica cada uma uma única vez |
| `ingest.py` | lê o CSV, normaliza e grava posts e métricas |
| `annotate.py` | anotações manuais (tema, gancho, experimento) |
| `analyze.py` | análise exploratória de um export, no terminal |
| `db.py`, `api.py` | API em FastAPI |
| `tests/` | testes; correm numa base própria, `contentdeck_test` |

### Modelo de dados

- `profiles` → `posts` → `metrics`. As métricas do export são acumuladas, então cada carga é uma **captura datada** (`captured_on`), única por post e dia. Isso dá a curva de crescimento de cada post.
- `latest_metrics`: visão com a captura mais recente de cada post. As rotas leem daqui.
- `experiments` e `experiment_posts`: uma hipótese, e os posts de cada variante.

## Testes

```bash
pytest tests/test_api.py          # o que está pronto: deve passar
pytest tests/test_exercicios.py   # rotas por implementar: falham até estarem prontas
```

## Exercícios da API

`/profiles/{handle}/summary` está completa e serve de modelo. Três rotas em `api.py` devolvem 501 e têm a especificação na docstring:

| # | Rota | O que se pratica |
|---|---|---|
| 1 | `/profiles/{handle}/posts` | parâmetros de consulta, ordenação segura, filtro, limite |
| 2 | `/profiles/{handle}/themes` | `GROUP BY` com medianas |
| 3 | `/profiles/{handle}/weekly` | agregação por semana com `date_trunc` |

Para cada uma: ler a docstring, escrever a consulta, correr `pytest tests/test_exercicios.py -k exercicio_N` até passar.

## Limitações conhecidas

- O caminho do TikTok em `ingest.py` nunca foi testado com um export real.
- `posts.external_id` é único no banco inteiro, não por perfil.
- Sem dados de retenção (tempo assistido): o export usado não os traz.
