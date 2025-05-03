// frontend/lib/api.ts
export type Stats = {
    total_followers: number
    new_followers: number
    unfollowers: number
  }
  
  export type FollowerSnapshot = {
    timestamp: string
    total_followers: number
  }
  
  export type ChangeEntry = {
    login: string
    avatar_url: string
    html_url: string
    timestamp: string
  }
  
  const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  
  async function fetchJson<T>(path: string): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
      credentials: "include",
    })
    if (!res.ok) {
      const body = await res.text().catch(() => "")
      throw new Error(`Failed to load ${path}: ${res.status} ${body}`)
    }
    return res.json()
  }
  
  export async function getPing(): Promise<{ status: string }> {
    return fetchJson("/ping")
  }
  
  export async function getFollowerStats(): Promise<Stats> {
    return fetchJson("/stats/followers")
  }
  
  export async function getFollowerTrends(): Promise<FollowerSnapshot[]> {
    return fetchJson("/stats/trends")
  }
  
  /**
   * Fetch the list of either "new" or "lost" followers
   */
  export async function getChangeHistory(
    type: "new" | "lost"
  ): Promise<ChangeEntry[]> {
    return fetchJson(`/stats/${type}`)
  }
  