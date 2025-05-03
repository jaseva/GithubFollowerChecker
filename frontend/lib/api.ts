export async function getPing() {
    const res = await fetch("http://localhost:8000/stats/ping");
    if (!res.ok) throw new Error("Network error");
    return res.json() as Promise<{ status: string; time: string }>;
  }
  