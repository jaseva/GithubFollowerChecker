// frontend/lib/api.ts

export type Stats = {
    total_followers: number;
    new_followers: number;
    unfollowers: number;
  };
  
  export type ChangeRecord = {
    timestamp: string;
    new?: number;
    lost?: number;
    count: number;
  };
  
  const BASE = "http://localhost:8000";
  
  async function handleFetch(path: string) {
    const res = await fetch(BASE + path, { credentials: "include" });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`Failed ${path}: ${res.status} ${txt}`);
    }
    return res.json();
  }
  
  export function getFollowerStats(): Promise<Stats> {
    return handleFetch("/stats/followers");
  }
  
  export function getChangeHistory(kind: "new" | "lost"): Promise<ChangeRecord[]> {
    return handleFetch(`/stats/${kind}`).then((body) => body.history);
  }
  