"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { Post } from "@/lib/api";
import { dateTime, dayMonth, dayNumber, fromDayNumber, int, monthName, pct, seconds, truncate } from "@/lib/format";

const M = { top: 26, right: 12, bottom: 44, left: 44 };
const HEIGHT = 340;
const MAX_BAR = 24;

/** Teto "redondo" do eixo e os seus degraus: 0 / 500 / 1.000 / 1.500. */
function scale(max: number) {
  const rough = max / 3;
  const pow = 10 ** Math.floor(Math.log10(Math.max(rough, 1)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= rough) ?? 10 * pow;
  const top = Math.ceil(max / step) * step;
  return { top, ticks: Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step) };
}

export default function Timeline({ posts, median, outlierIds }: { posts: Post[]; median: number; outlierIds: number[] }) {
  const wrap = useRef<HTMLDivElement>(null);
  // Largura real do contêiner; até ser medida, só a caixa vazia (sem salto de layout).
  const [width, setWidth] = useState(0);
  const [hideOutliers, setHideOutliers] = useState(false);
  const [active, setActive] = useState<number | null>(null);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.round(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const outliers = useMemo(() => new Set(outlierIds), [outlierIds]);
  const shown = hideOutliers ? posts.filter((p) => !outliers.has(p.id)) : posts;
  const hidden = posts.filter((p) => outliers.has(p.id));

  // Eixo X contínuo em dias: do primeiro ao último post, com os dias vazios à vista.
  const first = Math.min(...posts.map((p) => dayNumber(p.published_at)));
  const last = Math.max(...posts.map((p) => dayNumber(p.published_at)));
  const days = Array.from({ length: last - first + 1 }, (_, i) => first + i);

  const innerW = width - M.left - M.right;
  const innerH = HEIGHT - M.top - M.bottom;
  const slot = innerW / days.length;
  const { top, ticks } = scale(Math.max(...shown.map((p) => p.views), median, 1));
  const y = (v: number) => M.top + innerH - (v / top) * innerH;
  const labelEvery = Math.ceil(22 / slot);

  const byDay = new Map<number, Post[]>();
  for (const p of shown) {
    const d = dayNumber(p.published_at);
    byDay.set(d, [...(byDay.get(d) ?? []), p]);
  }

  const bars = days.flatMap((d, i) => {
    const list = byDay.get(d) ?? [];
    const w = Math.max(3, Math.min(MAX_BAR, (slot - 2) / Math.max(list.length, 1) - 2));
    const total = list.length * w + (list.length - 1) * 2;
    return list.map((p, j) => ({
      post: p,
      x: M.left + i * slot + (slot - total) / 2 + j * (w + 2),
      w,
      slotX: M.left + i * slot + (j * slot) / list.length,
      slotW: slot / list.length,
    }));
  });

  const current = bars.find((b) => b.post.id === active);
  const tipLeft = current ? Math.min(Math.max(current.x + current.w / 2, 120), width - 120) : 0;

  return (
    <div className="timeline">
      {hidden.length > 0 && (
        <div className="scope" role="group" aria-label="Posts mostrados na linha do tempo">
          <button type="button" aria-pressed={!hideOutliers} onClick={() => setHideOutliers(false)}>
            Todos os posts
          </button>
          <button type="button" aria-pressed={hideOutliers} onClick={() => setHideOutliers(true)}>
            Sem fora da curva
          </button>
          {hideOutliers && (
            <span className="scope-note">
              Oculto: {hidden.map((p) => `${dayMonth(p.published_at)}, ${int(p.views)} visualizações`).join("; ")}
            </span>
          )}
        </div>
      )}

      <div className="timeline-plot" ref={wrap} style={{ minHeight: HEIGHT }} onPointerLeave={() => setActive(null)}>
        {width > 0 && <svg width={width} height={HEIGHT} role="img"
          aria-label={`Visualizações por post, de ${dayMonth(posts[0].published_at)} a ${dayMonth(posts[posts.length - 1].published_at)}. Os valores estão na tabela no fim da página.`}>
          {ticks.map((t) => (
            <g key={t}>
              <line className={t === 0 ? "axis" : "grid"} x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} />
              <text className="tick" x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end">{int(t)}</text>
            </g>
          ))}

          {/* Régua de dias: traço maior e nome do mês onde a semana começa. */}
          {days.map((d, i) => {
            const { d: dom, m, weekday } = fromDayNumber(d);
            const cx = M.left + (i + 0.5) * slot;
            const monday = weekday === 1;
            const base = M.top + innerH;
            return (
              <g key={d}>
                <line className="axis" x1={cx} x2={cx} y1={base} y2={base + (monday ? 9 : 4)} />
                {i % labelEvery === 0 && (
                  <text className="tick" x={cx} y={base + 22} textAnchor="middle">{dom}</text>
                )}
                {(i === 0 || dom === 1) && (
                  <text className="tick month" x={cx} y={base + 38} textAnchor="middle">{monthName(m)}</text>
                )}
              </g>
            );
          })}

          {bars.map(({ post, x, w, slotX, slotW }) => {
            const out = outliers.has(post.id);
            const h = Math.max(1, (post.views / top) * innerH);
            const r = Math.min(4, w / 2, h);
            const yTop = M.top + innerH - h;
            return (
              <g key={post.id}>
                <path
                  className={`bar${out ? " outlier" : ""}${active === post.id ? " active" : ""}`}
                  d={`M${x},${M.top + innerH} V${yTop + r} Q${x},${yTop} ${x + r},${yTop} H${x + w - r} Q${x + w},${yTop} ${x + w},${yTop + r} V${M.top + innerH} Z`}
                />
                {out && (() => {
                  // rótulo à direita da barra; perto da borda, passa para a esquerda
                  const left = x + w + 100 > width - M.right;
                  const lx = left ? x - 8 : x + w + 8;
                  return (
                    <text className="callout" x={lx} y={yTop + 4} dy="0.7em" textAnchor={left ? "end" : "start"}>
                      <tspan className="callout-value">{int(post.views)}</tspan>
                      <tspan x={lx} dy="1.3em">fora da curva</tspan>
                    </text>
                  );
                })()}
                {/* Alvo de hover e foco: a faixa inteira do dia, não só os píxeis da barra. */}
                <rect
                  className="hit" x={slotX} y={M.top} width={slotW} height={innerH} tabIndex={0}
                  aria-label={`${dateTime(post.published_at)}: ${int(post.views)} visualizações`}
                  onPointerEnter={() => setActive(post.id)} onFocus={() => setActive(post.id)} onBlur={() => setActive(null)}
                />
              </g>
            );
          })}

          {median > 0 && (
            <g className="median">
              <line x1={M.left} x2={width - M.right} y1={y(median)} y2={y(median)} />
              <text x={width - M.right} y={y(median) - 6} textAnchor="end">mediana {int(median)}</text>
            </g>
          )}
        </svg>}

        {current && (
          <div className="tip" role="status" style={{ left: tipLeft, top: Math.max(y(current.post.views) - 12, 8) }}>
            <strong>{int(current.post.views)} visualizações</strong>
            <span>{dateTime(current.post.published_at)}</span>
            <dl>
              <div><dt>Alcance</dt><dd>{int(current.post.reach)}</dd></div>
              <div><dt>Engajamento</dt><dd>{pct(current.post.engagement_rate)}</dd></div>
              <div><dt>Duração</dt><dd>{seconds(current.post.duration_sec)}</dd></div>
              {current.post.theme && <div><dt>Tema</dt><dd>{current.post.theme}</dd></div>}
            </dl>
            {current.post.caption && <p>{truncate(current.post.caption, 90)}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
