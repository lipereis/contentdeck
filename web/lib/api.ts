// Tipos e leitura da API do ContentDeck (FastAPI). Corre só no servidor.

import { cache } from "react";

// Na Vercel, API_INTERNAL_URL é injetada pela ligação privada entre os serviços.
export const API_URL = process.env.API_INTERNAL_URL ?? process.env.API_URL ?? "http://localhost:8000";
export const HANDLE = process.env.PROFILE_HANDLE ?? "insidereismind";

export type Summary = {
  handle: string;
  platform: string;
  posts: number;
  captured_on: string | null;
  views: number;
  reach: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  follows: number;
  median_views: number | null;
  median_engagement_rate: number | null;
  top_post_share: number | null;
};

export type Post = {
  id: number;
  url: string | null;
  caption: string | null;
  published_at: string; // sem fuso: hora local do export
  duration_sec: number | null;
  theme: string | null;
  views: number;
  reach: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  follows: number;
  engagement_rate: number;
};

export type GroupStats = { posts: number; median_views: number; median_engagement_rate: number };
export type ThemeStats = GroupStats & { theme: string | null; follows: number };
export type WeekStats = GroupStats & { week_start: string; views: number };
export type DurationBucket = GroupStats & { bucket: string };

export type Outlier = {
  id: number;
  url: string | null;
  published_at: string;
  views: number;
  times_median: number;
  share_of_views: number;
};

export type Insights = {
  posts: number;
  median_views: number | null;
  outlier_factor: number;
  outliers: Outlier[];
  follows_per_1000_reach: number | null;
  likes_share_of_interactions: number | null;
  posts_without_comments: number;
  posts_without_shares: number;
  posts_without_saves: number;
  posts_without_follows: number;
  by_duration: DurationBucket[];
};

export type Experiment = {
  id: number;
  name: string;
  hypothesis: string | null;
  variable: string | null;
  started_on: string | null;
  ended_on: string | null;
  result: string | null;
  variants: (GroupStats & { variant: string; follows: number })[];
};

export type Deck = {
  summary: Summary;
  posts: Post[];
  themes: ThemeStats[];
  weekly: WeekStats[];
  insights: Insights;
  experiments: Experiment[];
};

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

async function get<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`);
  } catch {
    throw new ApiError(`sem resposta de ${API_URL}`);
  }
  if (!res.ok) throw new ApiError(`${path} respondeu ${res.status}`, res.status);
  return res.json() as Promise<T>;
}

// cache() do React: página, metadados e cartão de prévia pedem os mesmos dados no
// mesmo pedido; a API é consultada uma vez só.
export const loadDeck = cache(async (handle: string): Promise<Deck> => {
  // Um pedido só: em serverless, seis rotas seriam seis funções e seis ligações à base.
  return get<Deck>(`/profiles/${encodeURIComponent(handle)}/deck`);
});
