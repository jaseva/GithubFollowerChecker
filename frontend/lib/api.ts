export interface Stats { total_followers: number; new_followers: number; unfollowers: number; }
export interface Trends { labels: string[]; history: number[]; }
export interface Change { username: string; timestamp: string; }
export interface GitHubProfile {
  username: string;
  name: string | null;
  avatar_url: string | null;
  html_url: string;
  bio: string | null;
  public_repos: number;
  following: number;
  followers: number;
}

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Failed to load ${url}: ${res.status} ${body}`);
  }
  return res.json();
}

export function getFollowerStats(): Promise<Stats> {
  return fetchJSON<Stats>("http://localhost:8000/stats/followers");
}

export function getGitHubProfile(): Promise<GitHubProfile> {
  return fetchJSON<GitHubProfile>("http://localhost:8000/stats/profile");
}

export function getFollowerTrends(): Promise<Trends> {
  return fetchJSON<Trends>("http://localhost:8000/stats/trends");
}

export function getChangeHistory(type: "new"|"lost"): Promise<Change[]> {
  return fetchJSON<Change[]>(`http://localhost:8000/stats/history/${type}`);
}
