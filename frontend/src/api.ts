export type MarketBar = { date: string; close: number; volume: number };
export type MarketData = {
  ticker: string;
  symbol: string;
  currency: string;
  price: number;
  previous_close: number;
  change_pct: number;
  rsi_14: number | null;
  as_of: string;
  source: string;
  bars: MarketBar[];
  settled_dates: string[];
  disclaimer: string;
};

export type ReportSummary = {
  id: string;
  title: string;
  metadata: string[];
  has_html: boolean;
  modified: number;
};

export type CompanySearchResult = { symbol: string; name: string; exchange: string; quote_type: string };
export type SavedExperiment = {
  id: string;
  question: string;
  tickers: string[];
  dates: string[];
  model: string;
  run_a: string | null;
  run_b: string | null;
  modified: number;
};

export type Job = {
  id: string;
  kind: "analysis" | "experiment";
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  message: string;
  result: Record<string, unknown> | null;
  error: string | null;
};

const apiBase = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof data.detail === "string" ? data.detail : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data as T;
}

export const api = {
  health: () => request<{ status: string; api_key_configured: boolean; default_model: string; market_data: string }>("/api/health"),
  market: (ticker: string, period = "3mo") => request<MarketData>(`/api/market?ticker=${encodeURIComponent(ticker)}&period=${period}`),
  searchIndianCompanies: (query: string) => request<{ query: string; results: CompanySearchResult[]; source: string }>(`/api/companies/search?q=${encodeURIComponent(query)}`),
  startAnalysis: (payload: object) => request<{ job_id: string }>("/api/analyze", { method: "POST", body: JSON.stringify(payload) }),
  startExperiment: (payload: object) => request<{ job_id: string }>("/api/experiment", { method: "POST", body: JSON.stringify(payload) }),
  savedExperiments: () => request<SavedExperiment[]>("/api/experiments"),
  recalculateExperiment: (id: string) => request<Record<string, unknown>>(`/api/experiments/${encodeURIComponent(id)}/recalculate`, { method: "POST" }),
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  reports: () => request<ReportSummary[]>("/api/reports"),
  report: (id: string) => request<{ id: string; markdown: string }>(`/api/reports/${encodeURIComponent(id)}`),
};

export const reportHtmlUrl = (id: string) => `${apiBase}/api/reports/${encodeURIComponent(id)}/html`;
export const experimentFileUrl = (id: string, file: "comparison.html" | "paired_cells.csv") =>
  `${apiBase}/api/experiments/${encodeURIComponent(id)}/${file}`;
