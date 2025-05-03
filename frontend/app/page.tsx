"use client";
import { useEffect, useState } from "react";
import {
  getFollowerStats,
  getFollowerTrends,
  getChangeHistory,
  Stats,
  Trends,
  Change,
} from "../lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function Home() {
  const [stats, setStats] = useState<Stats>({ total_followers: 0, new_followers: 0, unfollowers: 0 });
  const [trends, setTrends] = useState<Trends>({ labels: [], history: [] });
  const [newList, setNewList] = useState<Change[]>([]);
  const [lostList, setLostList] = useState<Change[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFollowerStats()
      .then(setStats)
      .catch(() => setError("Failed to load snapshot"))
      .finally(() => {
        getFollowerTrends().then(setTrends).catch(() => setError("Failed to load trends"));
        getChangeHistory("new").then(setNewList).catch(() => setError("Failed to load new followers"));
        getChangeHistory("lost").then(setLostList).catch(() => setError("Failed to load lost followers"));
      });
  }, []);

  const data = trends.labels.map((ts, i) => ({
    date: new Date(ts).toLocaleDateString(),
    count: trends.history[i],
  }));

  return (
    <main className="p-8 space-y-4">
      <h1 className="text-3xl font-bold">GitHub Follower Dashboard</h1>
      <p className="text-gray-600">Interactive insights on your follower growth.</p>

      {error && <p className="text-red-600">{error}</p>}

      <div className="grid grid-cols-3 gap-4">
        <div className="card">Total Followers<br/><span className="text-2xl">{stats.total_followers}</span></div>
        <div className="card">New (24h)<br/><span className="text-green-600">+{stats.new_followers}</span></div>
        <div className="card">Lost (24h)<br/><span className="text-red-600">-{stats.unfollowers}</span></div>
      </div>

      <div className="card h-64">
        <ResponsiveContainer>
          <LineChart data={data}>
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#4F46E5" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="card">
          <h3>New Followers</h3>
          {newList.length > 0 ? newList.map(c => <p key={c.username}>{c.username}</p>) : <p>None</p>}
        </div>
        <div className="card">
          <h3>Lost Followers</h3>
          {lostList.length > 0 ? lostList.map(c => <p key={c.username}>{c.username}</p>) : <p>None</p>}
        </div>
      </div>
    </main>
  );
}
