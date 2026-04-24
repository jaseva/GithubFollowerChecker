export interface Stats {
  total_followers: number;
  new_followers: number;
  unfollowers: number;
  net_change: number;
}

export interface GitHubProfile {
  username: string;
  name: string | null;
  avatar_url: string | null;
  html_url: string;
  bio: string | null;
  public_repos: number;
  following: number;
  followers: number;
  company: string | null;
  location: string | null;
  created_at: string | null;
}

export interface Trends {
  labels: string[];
  history: number[];
}

export interface Change {
  username: string;
  timestamp: string;
}

export interface EnrichedChange extends Change {
  name: string | null;
  avatar_url: string | null;
  html_url: string;
  bio: string | null;
  public_repos: number;
  followers: number;
  following: number;
  company: string | null;
  location: string | null;
  created_at: string | null;
  signal_score: number;
  signal_label: string;
}

export interface DashboardMetrics {
  total_followers: number;
  following: number;
  net_24h: number;
  net_7d: number;
  net_30d: number;
  average_daily_growth: number;
  churn_rate: number;
  volatility_score: number;
  stability_score: number;
  snapshot_count: number;
  change_records_30d: number;
}

export interface DashboardHealth {
  api_status: "healthy" | "degraded" | "error";
  partial_data: boolean;
  stale_data: boolean;
  last_successful_sync: string | null;
  last_failed_sync: string | null;
  last_error: string | null;
  snapshot_count: number;
  expected_cadence_minutes: number | null;
  missed_snapshots: number;
  data_freshness_minutes: number | null;
  recent_sync_runs: SyncRunSummary[];
}

export interface SyncRunSummary {
  timestamp: string;
  status: "success" | "failure";
  follower_count: number | null;
  new_count: number;
  lost_count: number;
  error: string | null;
}

export interface ChartAnnotation {
  timestamp: string;
  kind: "spike" | "dip" | "gain" | "loss" | "peak" | "low";
  label: string;
  value: number;
  magnitude: number;
}

export interface DashboardData {
  generated_at: string;
  profile: GitHubProfile;
  stats: Stats;
  metrics: DashboardMetrics;
  trends: Trends;
  health: DashboardHealth;
  recent_new_followers: EnrichedChange[];
  recent_lost_followers: EnrichedChange[];
  all_new_followers: EnrichedChange[];
  all_lost_followers: EnrichedChange[];
  high_signal_new_followers: EnrichedChange[];
  annotations: ChartAnnotation[];
}

export type InsightRange = "24h" | "7d" | "30d";
export type InsightMode = "brief" | "executive" | "technical";

export interface InsightEvidence {
  label: string;
  value: string;
  source: string;
}

export interface InsightResponse {
  generated_at: string;
  range: InsightRange;
  mode: InsightMode;
  window_start: string | null;
  window_end: string | null;
  headline: string;
  summary: string;
  bullets: string[];
  evidence: InsightEvidence[];
  recommended_actions: string[];
  confidence: "high" | "medium" | "low";
  stale: boolean;
  data_warnings: string[];
}

export interface DashboardQueryResponse {
  generated_at: string;
  question: string;
  interpreted_intent: string;
  range: InsightRange;
  answer: string;
  evidence: InsightEvidence[];
  recommended_next_action: string;
  confidence: "high" | "medium" | "low";
  data_warnings: string[];
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function fetchJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`Failed to load ${path}: ${response.status} ${body}`);
  }

  return response.json();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    credentials: "include",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const responseBody = await response.text().catch(() => "");
    throw new Error(`Failed to load ${path}: ${response.status} ${responseBody}`);
  }

  return response.json();
}

export function getDashboard(refresh = false): Promise<DashboardData> {
  return fetchJSON<DashboardData>(`/stats/dashboard${refresh ? "?refresh=true" : ""}`);
}

export function getInsights(
  range: InsightRange,
  mode: InsightMode,
  refresh = false,
): Promise<InsightResponse> {
  return postJSON<InsightResponse>("/stats/insights", { range, mode, refresh });
}

export function askDashboardQuestion(
  question: string,
  range: InsightRange,
  refresh = false,
): Promise<DashboardQueryResponse> {
  return postJSON<DashboardQueryResponse>("/stats/query", { question, range, refresh });
}
