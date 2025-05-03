export type PingResponse = { status: string };
export type Stats = {
  total_followers: number;
  new_followers: number;
  unfollowers: number;
};

export async function getPing(): Promise<PingResponse> {
  const res = await fetch("http://localhost:8000/ping");
  if (!res.ok) throw new Error("Network error");
  return res.json();
}

export async function getFollowerStats(): Promise<Stats> {
  const res = await fetch("http://localhost:8000/stats/followers", {
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Failed to load stats: ${res.status} ${body}`);
  }
  return res.json();
}
