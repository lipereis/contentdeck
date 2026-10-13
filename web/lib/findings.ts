// Transforma os números da API em frases: o que os dados dizem e o que não
// permitem dizer. As regras são simples de propósito e ficam todas aqui.

import type { Deck } from "./api";
import { dayMonth, decimal, int, parts, pct, plural } from "./format";

export type Finding = { title: string; body: string };

const SMALL_SAMPLE = 30; // abaixo disto, tudo é indício
const DOMINANT = 0.7; // uma opção usada em mais de 70% dos posts não deixa comparar
// Os títulos só afirmam algo quando o número sustenta; fora disso ficam neutros.
const FEW_FOLLOWS_PER_1000 = 5; // menos de 5 seguidores por mil alcançados
const MOSTLY_LIKES = 0.7; // mais de 70% das interações são curtidas

function mostCommon<T>(values: T[]): { value: T; count: number } | null {
  const counts = new Map<T, number>();
  for (const v of values) counts.set(v, (counts.get(v) ?? 0) + 1);
  let best: { value: T; count: number } | null = null;
  for (const [value, count] of counts) if (!best || count > best.count) best = { value, count };
  return best;
}

export function headline({ summary, insights }: Deck): { main: string; second: string } {
  const main = summary.median_views == null ? "Sem posts ainda." : `Reel típico: ${int(summary.median_views)} views.`;
  const top = insights.outliers[0];
  const second = top
    ? `Um post fez ${pct(top.share_of_views, 0)} de tudo.`
    : `${plural(summary.posts, "post", "posts")}, nenhum fora da curva.`;
  return { main, second };
}

export function findings({ summary, insights, weekly }: Deck): Finding[] {
  const out: Finding[] = [];
  const n = summary.posts;
  if (!n) return out;

  const top = insights.outliers[0];
  if (top) {
    out.push({
      title: "Um post distorce os totais",
      body: `O de ${dayMonth(top.published_at)} teve ${int(top.views)} visualizações, ${decimal(top.times_median, 0)} vezes a mediana. Por isso o painel usa mediana: a média trataria esse post como rotina.`,
    });
  }

  const medians = weekly.map((w) => w.median_views);
  if (medians.length >= 3) {
    const rising = medians.every((m, i) => i === 0 || m > medians[i - 1]);
    const falling = medians.every((m, i) => i === 0 || m < medians[i - 1]);
    const range = `${int(Math.min(...medians))} e ${int(Math.max(...medians))}`;
    out.push(
      rising
        ? { title: "Visualizações subindo", body: `A mediana cresceu em todas as ${medians.length} semanas, entre ${range}.` }
        : falling
          ? { title: "Visualizações caindo", body: `A mediana caiu em todas as ${medians.length} semanas, entre ${range}.` }
          : { title: "Sem tendência de crescimento", body: `A mediana semanal oscilou entre ${range} visualizações, sem direção.` },
    );
  }

  if (insights.follows_per_1000_reach != null) {
    out.push({
      title: insights.follows_per_1000_reach < FEW_FOLLOWS_PER_1000 ? "Alcance quase não vira seguidor" : "Conversão em seguidores",
      body: `${plural(summary.follows, "seguidor ganho", "seguidores ganhos")} em ${plural(n, "post", "posts")}: ${decimal(insights.follows_per_1000_reach, 2)} a cada mil pessoas alcançadas. ${int(insights.posts_without_follows)} de ${n} posts não trouxeram nenhum.`,
    });
  }

  if (insights.likes_share_of_interactions != null) {
    out.push({
      title: insights.likes_share_of_interactions >= MOSTLY_LIKES ? "Engajamento é quase só curtida" : "Composição do engajamento",
      body: `${pct(insights.likes_share_of_interactions, 0)} das interações são curtidas. ${int(insights.posts_without_comments)} de ${n} posts não têm comentário e ${int(insights.posts_without_saves)} não foram salvos.`,
    });
  }

  const buckets = insights.by_duration;
  if (buckets.length >= 2) {
    const best = buckets.reduce((a, b) => (b.median_views > a.median_views ? b : a));
    const worst = buckets.reduce((a, b) => (b.median_views < a.median_views ? b : a));
    out.push({
      title: "Desempenho por duração",
      body: `A faixa "${worst.bucket}" teve a menor mediana (${int(worst.median_views)}, em ${plural(worst.posts, "post", "posts")}) e "${best.bucket}" a maior (${int(best.median_views)}). Com tão poucos posts por faixa, é indício fraco.`,
    });
  }

  return out;
}

export function limits({ summary, posts, themes }: Deck): Finding[] {
  const out: Finding[] = [];
  const n = summary.posts;
  if (!n) return out;

  if (n < SMALL_SAMPLE) {
    out.push({ title: "Amostra pequena", body: `São ${plural(n, "post", "posts")}. Tudo neste painel é indício, não conclusão.` });
  }

  const hour = mostCommon(posts.map((p) => parts(p.published_at).hour));
  if (hour && hour.count / n >= DOMINANT) {
    out.push({
      title: "Melhor horário",
      body: `${hour.count} de ${n} posts saíram às ${hour.value}h. Sem variar o horário, não há o que comparar.`,
    });
  }

  const tags = posts.flatMap((p) => [...new Set((p.caption ?? "").toLowerCase().match(/#[\p{L}\p{N}_]+/gu) ?? [])]);
  const tag = mostCommon(tags);
  if (tag && tag.count / n >= DOMINANT) {
    out.push({
      title: "Efeito das hashtags",
      body: `${tag.value} está em ${tag.count} de ${n} posts. As hashtags mudam pouco demais para medir o efeito de alguma.`,
    });
  }

  const thin = themes.filter((t) => t.theme && t.posts < 3);
  if (thin.length) {
    const list = thin.map((t) => `${t.theme} (${t.posts})`).join(", ");
    out.push({ title: "Comparação entre temas", body: `Poucos posts em: ${list}. Um resultado bom ali pode ser acaso.` });
  }

  out.push({
    title: "Posts recentes saem em desvantagem",
    body: "As métricas são acumuladas. Um post de três dias teve menos tempo para somar visualizações do que um de três semanas.",
  });

  return out;
}
