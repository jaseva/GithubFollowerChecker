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
  getChangeHistory,
  type Stats,
  type FollowerSnapshot,
  type ChangeEntry,
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
  const [newList, setNewList] = useState<ChangeEntry[]>([])
  const [lostList, setLostList] = useState<ChangeEntry[]>([])
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
        .catch(() => setError("Failed to load trends"))
      getChangeHistory("new")
        .then(setNewList)
        .catch(() => setError("Failed to load new followers"))
      getChangeHistory("lost")
        .then(setLostList)
        .catch(() => setError("Failed to load lost followers"))
    }
  }, [status])

  if (status === "loading") return <p>Loading session…</p>

  return (
    <main className="min-h-screen p-8 space-y-8">
      <header className="text-center space-y-2">
        <h1 className="text-4xl font-bold">GitHub Follower Dashboard</h1>
        <p className="text-muted-foreground">
          Interactive insights on your follower growth.
        </p>
      </header>

      {!session && (
        <Button onClick={() => signIn("github")}>
          Sign in with GitHub
        </Button>
      )}

      {session && (
        <section className="max-w-4xl mx-auto space-y-6">
          <div className="flex justify-between items-center">
            <p>
              Signed in as{" "}
              <strong>
                {session.user?.name || session.user?.email}
              </strong>
            </p>
            <Button variant="destructive" onClick={() => signOut()}>
              Sign out
            </Button>
          </div>

          {/* Ping */}
          <div className="space-y-2">
            <Button onClick={loadPing}>Ping backend</Button>
            {ping && (
              <p className="text-sm text-muted-foreground">Server: {ping}</p>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          {/* KPI cards */}
          {stats && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle>Total Followers</CardTitle>
                </CardHeader>
                <CardContent>
                  <span className="text-3xl">{stats.total_followers}</span>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>New (24h)</CardTitle>
                </CardHeader>
                <CardContent>
                  <span className="text-2xl text-green-600">
                    +{stats.new_followers}
                  </span>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Lost (24h)</CardTitle>
                </CardHeader>
                <CardContent>
                  <span className="text-2xl text-red-600">
                    -{stats.unfollowers}
                  </span>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Trend chart */}
          {trends.length > 0 && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Follower Growth</CardTitle>
              </CardHeader>
              <CardContent style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trends}>
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(t) =>
                        new Date(t).toLocaleDateString()
                      }
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(t) => new Date(t).toLocaleString()}
                    />
                    <Line
                      type="monotone"
                      dataKey="total_followers"
                      stroke="#8884d8"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* New vs Lost lists */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>New Followers</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 max-h-64 overflow-y-auto">
                {newList.length === 0 && <p className="text-sm">None</p>}
                {newList.map((u) => (
                  <div
                    key={u.login}
                    className="flex items-center space-x-3 py-2"
                  >
                    <img
                      src={u.avatar_url}
                      alt={u.login}
                      className="w-8 h-8 rounded-full"
                    />
                    <a
                      href={u.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium hover:underline"
                    >
                      {u.login}
                    </a>
                    <span className="text-xs text-muted-foreground">
                      {new Date(u.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Lost Followers</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 max-h-64 overflow-y-auto">
                {lostList.length === 0 && <p className="text-sm">None</p>}
                {lostList.map((u) => (
                  <div
                    key={u.login}
                    className="flex items-center space-x-3 py-2"
                  >
                    <img
                      src={u.avatar_url}
                      alt={u.login}
                      className="w-8 h-8 rounded-full"
                    />
                    <a
                      href={u.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium hover:underline"
                    >
                      {u.login}
                    </a>
                    <span className="text-xs text-muted-foreground">
                      {new Date(u.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </section>
      )}
    </main>
)
}
