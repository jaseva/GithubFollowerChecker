"use client"

import { useSession, signIn, signOut } from "next-auth/react"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card"
import {
  getPing,
  getFollowerStats,
  getFollowerTrends,
  type Stats,
  type FollowerSnapshot,
} from "@/lib/api"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts"

export default function Home() {
  const { data: session, status } = useSession()
  const [ping, setPing] = useState<string | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [trends, setTrends] = useState<FollowerSnapshot[]>([])
  const [error, setError] = useState<string | null>(null)

  async function loadPing() {
    try {
      const data = await getPing()
      setPing(data.status)
    } catch {
      setPing("backend unavailable")
    }
  }

  useEffect(() => {
    if (status === "authenticated") {
      getFollowerStats()
        .then(setStats)
        .catch(() => setError("Failed to load snapshot"))

      getFollowerTrends()
        .then(setTrends)
        .catch(() => setError("Failed to load trend data"))
    }
  }, [status])

  return (
    <main className="min-h-screen p-8 space-y-8">
      <header className="text-center space-y-2">
        <h1 className="text-4xl font-bold">GitHub Follower Dashboard</h1>
        <p className="text-muted-foreground">
          Interactive insights on your follower growth.
        </p>
      </header>

      {status === "loading" && <p>Loading session…</p>}
      {status !== "authenticated" && (
        <Button onClick={() => signIn("github")}>
          Sign in with GitHub
        </Button>
      )}

      {status === "authenticated" && (
        <section className="max-w-4xl mx-auto space-y-6">
          <div className="flex justify-between items-center">
            <p>
              Signed in as{" "}
              <strong>
                {session.user?.name ?? session.user?.email}
              </strong>
            </p>
            <Button variant="destructive" onClick={() => signOut()}>
              Sign out
            </Button>
          </div>

          {/* Ping */}
          <div className="space-y-2">
            <Button onClick={loadPing}>Ping backend</Button>
            {ping && <p className="text-sm text-muted-foreground">Server: {ping}</p>}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          {/* KPI cards */}
          {stats && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card>
                <CardHeader><CardTitle>Total Followers</CardTitle></CardHeader>
                <CardContent><span className="text-3xl">{stats.total_followers}</span></CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>New (24h)</CardTitle></CardHeader>
                <CardContent><span className="text-2xl text-green-600">+{stats.new_followers}</span></CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Lost (24h)</CardTitle></CardHeader>
                <CardContent><span className="text-2xl text-red-600">-{stats.unfollowers}</span></CardContent>
              </Card>
            </div>
          )}

          {/* Trend chart */}
          {trends.length > 0 && (
            <Card className="mt-6">
              <CardHeader><CardTitle>Follower Growth (Last Snapshots)</CardTitle></CardHeader>
              <CardContent style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trends}>
                    <XAxis dataKey="timestamp" tickFormatter={(ts) => new Date(ts).toLocaleDateString()} />
                    <YAxis />
                    <Tooltip labelFormatter={(ts) => new Date(ts).toLocaleString()} />
                    <Line type="monotone" dataKey="total_followers" stroke="#8884d8" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </section>
      )}
    </main>
  )
}
