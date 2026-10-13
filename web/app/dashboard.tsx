import BarList from "@/components/bar-list";
import PostsTable from "@/components/posts-table";
import Timeline from "@/components/timeline";
import { API_URL, ApiError, HANDLE, loadDeck, type Deck } from "@/lib/api";
import { findings, headline, limits } from "@/lib/findings";
import { dayMonth, int, longDate, pct, plural } from "@/lib/format";

export default async function Dashboard() {
  let deck: Deck;
  try {
    deck = await loadDeck(HANDLE);
  } catch (e) {
    return <Unavailable error={e} />;
  }

  const { summary, posts, themes, weekly, insights, experiments } = deck;
  if (!summary.posts) {
    return (
      <p className="status">
        @{HANDLE} ainda não tem posts carregados. Guarde um export em <code>data/</code> e rode <code>python ingest.py</code>.
      </p>
    );
  }

  const { main, second } = headline(deck);
  const outlierIds = insights.outliers.map((o) => o.id);

  return (
    <>
      <section className="thesis">
        <h1>
          {main} <span className="thesis-second">{second}</span>
        </h1>
        {/* Claquete: os campos que identificam a captura que está na tela. */}
        <dl className="slate">
          <div><dt>Perfil</dt><dd>@{summary.handle}</dd></div>
          <div><dt>Plataforma</dt><dd>{summary.platform}</dd></div>
          <div><dt>Captura</dt><dd>{summary.captured_on ? longDate(summary.captured_on) : "—"}</dd></div>
          <div><dt>Posts</dt><dd>{int(summary.posts)}</dd></div>
          <div><dt>Visualizações</dt><dd>{int(summary.views)}</dd></div>
          <div><dt>Seguidores ganhos</dt><dd>{int(summary.follows)}</dd></div>
        </dl>
      </section>

      <section aria-labelledby="t-timeline">
        <h2 id="t-timeline">Linha do tempo</h2>
        <p className="lede">
          Visualizações de cada post no dia em que saiu. Dias vazios são dias sem publicar.
        </p>
        <Timeline posts={posts} median={summary.median_views ?? 0} outlierIds={outlierIds} />
      </section>

      <div className="readings">
        <section aria-labelledby="t-findings">
          <h2 id="t-findings">O que os números dizem</h2>
          <ul className="notes">
            {findings(deck).map((f) => (
              <li key={f.title}><h3>{f.title}</h3><p>{f.body}</p></li>
            ))}
          </ul>
        </section>
        <section aria-labelledby="t-limits" className="limits">
          <h2 id="t-limits">O que não dá para concluir</h2>
          <ul className="notes">
            {limits(deck).map((f) => (
              <li key={f.title}><h3>{f.title}</h3><p>{f.body}</p></li>
            ))}
          </ul>
        </section>
      </div>

      <section aria-labelledby="t-groups">
        <h2 id="t-groups">Mediana de visualizações por grupo</h2>
        <div className="groups">
          <BarList
            title="Por semana de publicação"
            rows={weekly.map((w) => ({
              label: `sem. ${dayMonth(w.week_start)}`,
              value: w.median_views,
              note: `${plural(w.posts, "post", "posts")} · eng. ${pct(w.median_engagement_rate)}`,
            }))}
          />
          <BarList
            title="Por duração"
            rows={insights.by_duration.map((b) => ({
              label: b.bucket,
              value: b.median_views,
              note: `${plural(b.posts, "post", "posts")} · eng. ${pct(b.median_engagement_rate)}`,
            }))}
          />
          <BarList
            title="Por tema"
            rows={themes.map((t) => ({
              label: t.theme ?? "sem tema",
              value: t.median_views,
              note: `${plural(t.posts, "post", "posts")} · eng. ${pct(t.median_engagement_rate)}`,
            }))}
          />
        </div>
      </section>

      <section aria-labelledby="t-experiments">
        <h2 id="t-experiments">Experimentos</h2>
        {experiments.length === 0 ? (
          <p className="empty">
            Nenhum experimento ainda. Para abrir o primeiro, preencha as colunas <code>experiment</code> e{" "}
            <code>variant</code> em <code>data/annotations.csv</code> e rode <code>python annotate.py load</code>.
          </p>
        ) : (
          <div className="groups">
            {experiments.map((e) => (
              <BarList
                key={e.id}
                title={e.name}
                caption={e.hypothesis ?? undefined}
                rows={e.variants.map((v) => ({
                  label: v.variant,
                  value: v.median_views,
                  note: `${plural(v.posts, "post", "posts")} · eng. ${pct(v.median_engagement_rate)} · ${plural(v.follows, "seguidor", "seguidores")}`,
                }))}
              />
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="t-posts">
        <h2 id="t-posts">Todos os posts</h2>
        <PostsTable posts={posts} outlierIds={outlierIds} />
      </section>
    </>
  );
}

function Unavailable({ error }: { error: unknown }) {
  const notFound = error instanceof ApiError && error.status === 404;
  return (
    <div className="status" role="alert">
      {notFound ? (
        <p>
          O perfil @{HANDLE} não existe no banco. Carregue um export com <code>python ingest.py</code>.
        </p>
      ) : (
        <p>
          A API não respondeu em <code>{API_URL}</code>. Inicie com <code>uvicorn api:app</code> na pasta do projeto e
          recarregue esta página.
        </p>
      )}
    </div>
  );
}
