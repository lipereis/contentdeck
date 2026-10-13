// Formatação pt-BR. As datas da API não têm fuso (hora local do export), por isso
// são lidas por partes do texto, sem passar por Date com fuso do navegador.

const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const WEEKDAYS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

const nf = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

export const int = (n: number) => nf.format(Math.round(n));

export const pct = (fraction: number, digits = 1) =>
  `${(fraction * 100).toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;

export const decimal = (n: number, digits = 1) =>
  n.toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export type Parts = { y: number; m: number; d: number; hour: number; minute: number };

export function parts(iso: string): Parts {
  const [date, time = "00:00"] = iso.split("T");
  const [y, m, d] = date.split("-").map(Number);
  const [hour, minute] = time.split(":").map(Number);
  return { y, m, d, hour, minute };
}

/** Número de dias desde a época, para medir distâncias entre datas sem fuso. */
export const dayNumber = (iso: string) => {
  const { y, m, d } = parts(iso);
  return Math.round(Date.UTC(y, m - 1, d) / 86_400_000);
};

export const fromDayNumber = (n: number) => {
  const dt = new Date(n * 86_400_000);
  return { y: dt.getUTCFullYear(), m: dt.getUTCMonth() + 1, d: dt.getUTCDate(), weekday: dt.getUTCDay() };
};

export const weekday = (iso: string) => WEEKDAYS[fromDayNumber(dayNumber(iso)).weekday];
export const monthName = (m: number) => MONTHS[m - 1];

const two = (n: number) => String(n).padStart(2, "0");

/** 24/09 */
export const dayMonth = (iso: string) => {
  const p = parts(iso);
  return `${two(p.d)}/${two(p.m)}`;
};

/** 12 out 2026 */
export const longDate = (iso: string) => {
  const p = parts(iso);
  return `${p.d} ${MONTHS[p.m - 1]} ${p.y}`;
};

/** qui 24/09 · 15h58 */
export const dateTime = (iso: string) => {
  const p = parts(iso);
  return `${weekday(iso)} ${dayMonth(iso)} · ${p.hour}h${two(p.minute)}`;
};

export const seconds = (s: number | null) => (s == null ? "—" : `${s} s`);

export const plural = (n: number, one: string, many: string) => `${int(n)} ${n === 1 ? one : many}`;

export const truncate = (text: string, max: number) =>
  text.length <= max ? text : `${text.slice(0, max - 1).trimEnd()}…`;
