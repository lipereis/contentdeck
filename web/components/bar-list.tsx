import { int } from "@/lib/format";

type Row = { label: string; value: number; note?: string };

/**
 * Barras horizontais numa escala comum, uma cor só: os grupos não têm identidade
 * de cor, o comprimento já diz tudo. Valor escrito na ponta de cada barra.
 */
export default function BarList({ title, caption, rows }: { title: string; caption?: string; rows: Row[] }) {
  const max = Math.max(...rows.map((r) => r.value), 1);
  return (
    <figure className="barlist">
      <figcaption>
        <h3>{title}</h3>
        {caption && <p>{caption}</p>}
      </figcaption>
      {rows.length === 0 ? (
        <p className="empty">Sem dados para este grupo.</p>
      ) : (
        <ul>
          {rows.map((r) => (
            <li key={r.label} title={`${r.label}: ${int(r.value)} visualizações (mediana)${r.note ? ` · ${r.note}` : ""}`}>
              <span className="barlist-label">{r.label}</span>
              <span className="barlist-track">
                <span className="barlist-bar" style={{ width: `${(r.value / max) * 100}%` }} />
                <span className="barlist-value">{int(r.value)}</span>
              </span>
              {r.note && <span className="barlist-note">{r.note}</span>}
            </li>
          ))}
        </ul>
      )}
    </figure>
  );
}
