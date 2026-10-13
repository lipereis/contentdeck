"use client";

import { useMemo, useState } from "react";

import type { Post } from "@/lib/api";
import { dateTime, int, pct, seconds, truncate } from "@/lib/format";

type Key = "published_at" | "duration_sec" | "views" | "reach" | "engagement_rate" | "likes" | "comments" | "shares" | "saves" | "follows";

const COLUMNS: { key: Key; label: string; title?: string }[] = [
  { key: "published_at", label: "Publicado" },
  { key: "duration_sec", label: "Duração" },
  { key: "views", label: "Views", title: "Visualizações" },
  { key: "reach", label: "Alcance" },
  { key: "engagement_rate", label: "Engaj.", title: "Interações divididas pelo alcance" },
  { key: "likes", label: "Curt.", title: "Curtidas" },
  { key: "comments", label: "Com.", title: "Comentários" },
  { key: "shares", label: "Comp.", title: "Compartilhamentos" },
  { key: "saves", label: "Salv.", title: "Salvamentos" },
  { key: "follows", label: "Seg.", title: "Seguidores ganhos" },
];

export default function PostsTable({ posts, outlierIds }: { posts: Post[]; outlierIds: number[] }) {
  const [sort, setSort] = useState<{ key: Key; desc: boolean }>({ key: "published_at", desc: true });
  const outliers = useMemo(() => new Set(outlierIds), [outlierIds]);

  const rows = useMemo(() => {
    const dir = sort.desc ? -1 : 1;
    return [...posts].sort((a, b) => {
      const x = a[sort.key] ?? -1;
      const y = b[sort.key] ?? -1;
      return (x < y ? -1 : x > y ? 1 : 0) * dir;
    });
  }, [posts, sort]);

  const cell = (p: Post, key: Key) => {
    if (key === "published_at") return dateTime(p.published_at);
    if (key === "duration_sec") return seconds(p.duration_sec);
    if (key === "engagement_rate") return pct(p.engagement_rate);
    return int(p[key]);
  };

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col" className="text">Legenda</th>
            {COLUMNS.map((c) => (
              <th key={c.key} scope="col" title={c.title}
                aria-sort={sort.key === c.key ? (sort.desc ? "descending" : "ascending") : "none"}>
                <button type="button"
                  onClick={() => setSort((s) => ({ key: c.key, desc: s.key === c.key ? !s.desc : true }))}>
                  {c.label}
                  <span aria-hidden="true">{sort.key === c.key ? (sort.desc ? " ↓" : " ↑") : ""}</span>
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              <th scope="row" className="text">
                {p.url ? (
                  <a href={p.url} target="_blank" rel="noreferrer">{truncate(p.caption || "sem legenda", 58)}</a>
                ) : (
                  truncate(p.caption || "sem legenda", 58)
                )}
                {outliers.has(p.id) && <span className="flag">fora da curva</span>}
              </th>
              {COLUMNS.map((c) => (
                <td key={c.key}>{cell(p, c.key)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
