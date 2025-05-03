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
  
  const API_BASE = "http://localhost:8000"
  
  export async function getPing(): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/ping`)
    if (!res.ok) throw new Error("Network error")
    return res.json()
  }
  
  export async function getFollowerStats(): Promise<Stats> {
    const res = await fetch(`${API_BASE}/stats/followers`, {
      credentials: "include",
    })
    if (!res.ok) {
      const txt = await res.text().catch(() => "")
      throw new Error(`Failed to load stats: ${res.status} ${txt}`)
    }
    return res.json()
  }
  
  export async function getFollowerTrends(): Promise<FollowerSnapshot[]> {
    const res = await fetch(`${API_BASE}/stats/trends`, {
      credentials: "include",
    })
    if (!res.ok) {
      const txt = await res.text().catch(() => "")
      throw new Error(`Failed to load trends: ${res.status} ${txt}`)
    }
    return res.json()
  }
  