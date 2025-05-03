"use client";

import { useSession, signIn, signOut } from "next-auth/react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { getPing, getFollowerStats, Stats } from "@/lib/api";

export default function Home() {
  const { data: session, status } = useSession();
  const [ping, setPing] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadPing() {
    try {
      const data = await getPing();
      setPing(data.status);
    } catch {
      setPing("backend unavailable");
    }
  }

  useEffect(() => {
    if (status === "authenticated") {
      getFollowerStats()
        .then(setStats)
        .catch(() => setError("Failed to load follower stats"));
    }
  }, [status]);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 text-center space-y-8">
      <div className="space-y-2">
        <h1 className="text-4xl font-bold">GitHub Follower Checker</h1>
        <p className="text-muted-foreground">
          Track and analyze your followers with AI and data insights.
        </p>
      </div>

      {status === "loading" ? (
        <p>Loading session…</p>
      ) : !session ? (
        <Button onClick={() => signIn("github")}>
          Sign in with GitHub
        </Button>
      ) : (
        <div className="space-y-6 max-w-md w-full">
          <p className="text-lg">
            Signed in as{" "}
            <strong>
              {session.user?.name ?? session.user?.email}
            </strong>
          </p>

          {/* ping backend */}
          <div className="space-y-2">
            <Button onClick={loadPing}>Ping backend</Button>
            {ping && (
              <p className="text-sm text-muted-foreground">
                Server status: {ping}
              </p>
            )}
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          {stats && (
            <Card className="w-full">
              <CardHeader>
                <CardTitle>Follower Snapshot</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <span className="text-2xl font-semibold">
                    {stats.total_followers}
                  </span>
                  <p className="text-sm text-muted-foreground">
                    Total Followers
                  </p>
                </div>
                <div className="flex justify-between gap-4">
                  <div>
                    <span className="text-lg font-semibold text-green-600">
                      +{stats.new_followers}
                    </span>
                    <p className="text-sm text-muted-foreground">
                      New (24h)
                    </p>
                  </div>
                  <div>
                    <span className="text-lg font-semibold text-red-600">
                      –{stats.unfollowers}
                    </span>
                    <p className="text-sm text-muted-foreground">
                      Unfollowers
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <Button
            variant="destructive"
            onClick={() => signOut()}
          >
            Sign out
          </Button>
        </div>
      )}
    </main>
  );
}
