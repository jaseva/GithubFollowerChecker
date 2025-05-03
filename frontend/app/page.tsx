"use client"

import { useSession, signIn, signOut } from "next-auth/react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { getPing } from "@/lib/api"

export default function Home() {
  const { data: session, status } = useSession()
  const [ping, setPing] = useState<string | null>(null)

  async function loadPing() {
    try {
      const data = await getPing()
      setPing(data.time)
    } catch {
      setPing("backend unavailable")
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 text-center">
      <h1 className="text-4xl font-bold mb-4">GitHub Follower Checker</h1>
      <p className="text-muted-foreground mb-8">
        Track and analyze your followers with AI and data insights.
      </p>

      {status === "loading" ? (
        <p>Loading session…</p>
      ) : session ? (
        <div className="space-y-4">
          <p className="text-lg">
            Signed in as <strong>{session.user?.name ?? session.user?.email}</strong>
          </p>

          <Button onClick={loadPing}>Ping backend</Button>
          {ping && <p className="text-sm text-muted-foreground">Server time: {ping}</p>}

          <Button variant="destructive" onClick={() => signOut()}>
            Sign out
          </Button>
        </div>
      ) : (
        <Button onClick={() => signIn("github")}>Sign in with GitHub</Button>
      )}
    </main>
  )
}
