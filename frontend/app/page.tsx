"use client";

import Image from "next/image";
import type { ComponentType } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Github,
  GitBranch,
  Radio,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  UserMinus,
  UserPlus,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipProps } from "recharts";
import {
  Change,
  GitHubProfile,
  Stats,
  Trends,
  getChangeHistory,
  getFollowerStats,
  getFollowerTrends,
  getGitHubProfile,
} from "../lib/api";

type RangeKey = "7d" | "30d" | "all";

type ChartPoint = {
  count: number;
  raw: Date;
  axisLabel: string;
  tooltipLabel: string;
  change: number;
};

const ranges: Array<{ key: RangeKey; label: string }> = [
  { key: "7d", label: "7D" },
  { key: "30d", label: "30D" },
  { key: "all", label: "All" },
];

const numberFormatter = new Intl.NumberFormat("en-US");
const percentFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
});

function formatAxisDate(date: Date) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatFullDate(date: Date) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function signedNumber(value: number) {
  if (value > 0) return `+${numberFormatter.format(value)}`;
  return numberFormatter.format(value);
}

function ChartTooltip({ active, payload }: TooltipProps<number, string>) {
  const point = payload?.[0]?.payload as ChartPoint | undefined;

  if (!active || !point) return null;

  return (
    <div className="rounded-lg border border-[#ccd7cf] bg-[#fffdf8] px-4 py-3 shadow-lg">
      <p className="text-sm font-semibold text-[#17201d]">{point.tooltipLabel}</p>
      <p className="mt-1 text-2xl font-semibold text-[#0f766e]">
        {numberFormatter.format(point.count)}
      </p>
      <p className="mt-1 text-xs text-[#66736d]">
        Previous point: {signedNumber(point.change)}
      </p>
    </div>
  );
}

function KpiCard({
  title,
  value,
  detail,
  tone,
  icon: Icon,
}: {
  title: string;
  value: string;
  detail: string;
  tone: "green" | "rose" | "blue" | "amber";
  icon: ComponentType<{ className?: string }>;
}) {
  const tones = {
    green: "border-[#bddccd] bg-[#f1faf5] text-[#087f5b]",
    rose: "border-[#f0c3c3] bg-[#fff5f3] text-[#b42318]",
    blue: "border-[#bfd4e8] bg-[#f2f7fb] text-[#25637e]",
    amber: "border-[#ead391] bg-[#fff8df] text-[#946200]",
  };

  return (
    <article className="min-w-0 rounded-lg border border-[#d9ddd4] bg-[#fffdf8] p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-xs font-medium uppercase tracking-[0.08em] text-[#66736d]">
            {title}
          </p>
          <p className="mt-2 truncate text-3xl font-semibold leading-none text-[#17201d]">
            {value}
          </p>
        </div>
        <div className={`shrink-0 rounded-lg border p-2 ${tones[tone]}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-3 truncate text-xs text-[#66736d]">{detail}</p>
    </article>
  );
}

function ActivityPanel({
  title,
  items,
  emptyText,
  tone,
  icon: Icon,
}: {
  title: string;
  items: Change[];
  emptyText: string;
  tone: "green" | "rose";
  icon: ComponentType<{ className?: string }>;
}) {
  const colors =
    tone === "green"
      ? "border-[#bddccd] bg-[#effaf4] text-[#087f5b]"
      : "border-[#f0c3c3] bg-[#fff4f2] text-[#b42318]";

  return (
    <section className="min-h-0 rounded-lg border border-[#d9ddd4] bg-[#fffdf8] p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#17201d]">{title}</h2>
          <p className="mt-0.5 text-xs text-[#66736d]">Last 24 hours</p>
        </div>
        <div className={`rounded-lg border p-2 ${colors}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {items.length > 0 ? (
          items.slice(0, 3).map((item) => (
            <div
              key={`${item.username}-${item.timestamp}`}
              className="flex items-center justify-between border-b border-[#edf0ea] pb-2 last:border-b-0 last:pb-0"
            >
              <p className="truncate text-sm font-medium text-[#17201d]">{item.username}</p>
              <span className={`shrink-0 rounded-lg border px-2 py-1 text-xs ${colors}`}>
                {tone === "green" ? "Gained" : "Lost"}
              </span>
            </div>
          ))
        ) : (
          <div className="rounded-lg border border-dashed border-[#cfd7ce] bg-[#faf8f1] px-3 py-4 text-center">
            <p className="text-sm font-medium text-[#17201d]">{emptyText}</p>
            <p className="mt-1 text-xs text-[#66736d]">No account changes recorded.</p>
          </div>
        )}
      </div>
    </section>
  );
}

export default function Home() {
  const [stats, setStats] = useState<Stats>({
    total_followers: 0,
    new_followers: 0,
    unfollowers: 0,
  });
  const [trends, setTrends] = useState<Trends>({ labels: [], history: [] });
  const [profile, setProfile] = useState<GitHubProfile | null>(null);
  const [newList, setNewList] = useState<Change[]>([]);
  const [lostList, setLostList] = useState<Change[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [range, setRange] = useState<RangeKey>("30d");
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const nextStats = await getFollowerStats();
      setStats(nextStats);

      const [profileResult, trendsResult, newResult, lostResult] = await Promise.allSettled([
        getGitHubProfile(),
        getFollowerTrends(),
        getChangeHistory("new"),
        getChangeHistory("lost"),
      ]);

      if (profileResult.status === "fulfilled") setProfile(profileResult.value);
      if (trendsResult.status === "fulfilled") {
        setTrends(trendsResult.value);
      } else {
        setError("Follower trend history is unavailable.");
      }
      if (newResult.status === "fulfilled") setNewList(newResult.value);
      if (lostResult.status === "fulfilled") setLostList(lostResult.value);

      setLastSync(new Date());
    } catch {
      setError("The dashboard could not reach the follower API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const allPoints = useMemo<ChartPoint[]>(() => {
    return trends.labels
      .map((label, index) => {
        const raw = new Date(label);
        const previous = trends.history[index - 1] ?? trends.history[index] ?? 0;
        const count = trends.history[index] ?? 0;

        return {
          count,
          raw,
          axisLabel: formatAxisDate(raw),
          tooltipLabel: formatFullDate(raw),
          change: count - previous,
        };
      })
      .filter((point) => !Number.isNaN(point.raw.getTime()));
  }, [trends]);

  const chartData = useMemo(() => {
    if (range === "all" || allPoints.length === 0) return allPoints;

    const latest = allPoints[allPoints.length - 1].raw.getTime();
    const days = range === "7d" ? 7 : 30;
    const cutoff = latest - days * 24 * 60 * 60 * 1000;

    return allPoints.filter((point) => point.raw.getTime() >= cutoff);
  }, [allPoints, range]);

  const counts = chartData.length > 0 ? chartData.map((point) => point.count) : [stats.total_followers];
  const currentFollowers = stats.total_followers || profile?.followers || counts[counts.length - 1] || 0;
  const displayData =
    chartData.length > 0
      ? chartData
      : [
          {
            count: currentFollowers,
            raw: new Date(),
            axisLabel: "Now",
            tooltipLabel: "Current snapshot",
            change: 0,
          },
        ];
  const baseline = counts[0] ?? currentFollowers;
  const netChange = currentFollowers - baseline;
  const peak = Math.max(...counts, currentFollowers);
  const low = Math.min(...counts, currentFollowers);
  const average = Math.round(counts.reduce((sum, count) => sum + count, 0) / counts.length);
  const net24 = stats.new_followers - stats.unfollowers;
  const percentChange = baseline > 0 ? (netChange / baseline) * 100 : 0;
  const latestPoint = allPoints[allPoints.length - 1] ?? null;
  const firstPoint = allPoints[0] ?? null;
  const monitoringDays =
    firstPoint && latestPoint
      ? Math.max(1, Math.ceil((latestPoint.raw.getTime() - firstPoint.raw.getTime()) / 86400000))
      : 1;
  const stability =
    currentFollowers > 0 ? Math.max(0, 100 - (Math.abs(netChange) / currentFollowers) * 100) : 100;

  const profileTitle = profile?.name || profile?.username || "GitHub account";
  const profileHandle = profile?.username ? `@${profile.username}` : "Follower tracker";
  const statusTone = error ? "text-[#b42318]" : "text-[#087f5b]";

  return (
    <main className="min-h-screen bg-[#f5f2e9] text-[#17201d] xl:h-screen xl:overflow-hidden">
      <header className="border-b border-[#d9ddd4] bg-[#fffdf8]">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-3 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-[#17201d] text-[#fffdf8] shadow-sm">
              <Github className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold leading-tight">GitHub Follower Intelligence</h1>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[#66736d]">
                <span>{profileHandle}</span>
                <span className="h-1 w-1 rounded-full bg-[#aab5ad]" />
                <span className={`inline-flex items-center gap-1.5 ${statusTone}`}>
                  <Radio className="h-3.5 w-3.5" />
                  {error ? "Attention needed" : "Live data"}
                </span>
                {lastSync && (
                  <>
                    <span className="h-1 w-1 rounded-full bg-[#aab5ad]" />
                    <span>{formatFullDate(lastSync)}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg border border-[#d6ded6] bg-[#f7f5ee] p-1">
              {ranges.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setRange(item.key)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    range === item.key
                      ? "bg-[#17201d] text-[#fffdf8] shadow-sm"
                      : "text-[#596962] hover:bg-[#ebe8de]"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={loadDashboard}
              disabled={loading}
              title="Refresh dashboard data"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#cfd8d1] bg-[#fffdf8] px-3 py-2 text-xs font-semibold text-[#17201d] shadow-sm transition hover:bg-[#f2efe6] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1500px] gap-4 px-5 py-4 xl:h-[calc(100vh-76px)] xl:grid-rows-[104px_minmax(0,1fr)_150px]">
        {error && (
          <div className="rounded-lg border border-[#f0c3c3] bg-[#fff4f2] px-4 py-3 text-sm font-medium text-[#b42318] xl:absolute xl:right-5 xl:top-[84px] xl:z-10">
            {error}
          </div>
        )}

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            title="Total followers"
            value={numberFormatter.format(currentFollowers)}
            detail={`${numberFormatter.format(profile?.following ?? 0)} following`}
            tone="blue"
            icon={Users}
          />
          <KpiCard
            title="Net movement"
            value={signedNumber(net24)}
            detail="24-hour follower movement"
            tone={net24 < 0 ? "rose" : "green"}
            icon={net24 < 0 ? ArrowDownRight : ArrowUpRight}
          />
          <KpiCard
            title="New followers"
            value={`+${numberFormatter.format(stats.new_followers)}`}
            detail={`${numberFormatter.format(newList.length)} change records`}
            tone="green"
            icon={UserPlus}
          />
          <KpiCard
            title="Lost followers"
            value={`-${numberFormatter.format(stats.unfollowers)}`}
            detail={`${numberFormatter.format(lostList.length)} churn records`}
            tone="rose"
            icon={UserMinus}
          />
        </section>

        <section className="grid min-h-0 gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
          <section className="min-h-[360px] rounded-lg border border-[#d9ddd4] bg-[#fffdf8] p-4 shadow-sm xl:min-h-0">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.08em] text-[#0f766e]">
                  <TrendingUp className="h-4 w-4" />
                  Audience trajectory
                </div>
                <h2 className="mt-1 text-xl font-semibold text-[#17201d]">Follower growth</h2>
              </div>
              <div className="flex shrink-0 gap-2 text-xs">
                <span className="rounded-lg border border-[#bddccd] bg-[#f1faf5] px-2.5 py-1 text-[#087f5b]">
                  {percentFormatter.format(percentChange)}%
                </span>
                <span className="rounded-lg border border-[#e7d59d] bg-[#fff8df] px-2.5 py-1 text-[#946200]">
                  {numberFormatter.format(displayData.length)} pts
                </span>
              </div>
            </div>

            <div className="mt-3 h-[calc(100%-112px)] min-h-[250px] xl:min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={displayData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="followerFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0f766e" stopOpacity={0.28} />
                      <stop offset="95%" stopColor="#0f766e" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#e6e2d8" strokeDasharray="4 6" vertical={false} />
                  <XAxis
                    dataKey="axisLabel"
                    tickLine={false}
                    axisLine={{ stroke: "#cfd8d1" }}
                    tick={{ fill: "#66736d", fontSize: 12 }}
                    minTickGap={24}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#66736d", fontSize: 12 }}
                    width={48}
                    domain={["dataMin - 2", "dataMax + 2"]}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={{ stroke: "#0f766e", strokeWidth: 1 }} />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#0f766e"
                    strokeWidth={3}
                    fill="url(#followerFill)"
                    activeDot={{ r: 5, stroke: "#fffdf8", strokeWidth: 2 }}
                    dot={{ r: 3, strokeWidth: 2, fill: "#fffdf8" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-3 grid grid-cols-4 gap-2 border-t border-[#edf0ea] pt-3">
              {[
                ["Baseline", baseline],
                ["Peak", peak],
                ["Average", average],
                ["Low", low],
              ].map(([label, value]) => (
                <div key={label}>
                  <p className="text-[11px] text-[#66736d]">{label}</p>
                  <p className="mt-0.5 text-base font-semibold">{numberFormatter.format(Number(value))}</p>
                </div>
              ))}
            </div>
          </section>

          <aside className="grid min-h-0 gap-4 xl:grid-rows-[minmax(0,1fr)_150px]">
            <section className="min-h-0 rounded-lg border border-[#d9ddd4] bg-[#fffdf8] p-4 shadow-sm">
              <div className="flex items-start gap-3">
                {profile?.avatar_url ? (
                  <Image
                    src={profile.avatar_url}
                    alt={`${profileTitle} avatar`}
                    width={56}
                    height={56}
                    className="h-14 w-14 rounded-lg border border-[#d9ddd4] object-cover"
                  />
                ) : (
                  <div className="flex h-14 w-14 items-center justify-center rounded-lg border border-[#d9ddd4] bg-[#f2efe6]">
                    <Github className="h-6 w-6 text-[#17201d]" />
                  </div>
                )}
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-semibold text-[#17201d]">{profileTitle}</h2>
                  <p className="mt-0.5 text-xs text-[#66736d]">{profileHandle}</p>
                  {profile?.html_url && (
                    <a
                      href={profile.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-[#0f766e] hover:text-[#075f59]"
                    >
                      View profile
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </div>

              {profile?.bio && (
                <p className="mt-3 line-clamp-3 text-xs leading-5 text-[#4f5f58]">{profile.bio}</p>
              )}

              <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[#edf0ea] pt-3">
                <div>
                  <p className="text-[11px] text-[#66736d]">Repositories</p>
                  <p className="mt-0.5 text-base font-semibold">
                    {numberFormatter.format(profile?.public_repos ?? 0)}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-[#66736d]">Following</p>
                  <p className="mt-0.5 text-base font-semibold">
                    {numberFormatter.format(profile?.following ?? 0)}
                  </p>
                </div>
              </div>
            </section>

            <section className="rounded-lg border border-[#d9ddd4] bg-[#fffdf8] p-4 shadow-sm">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[#0f766e]" />
                <h2 className="text-base font-semibold text-[#17201d]">Signal quality</h2>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
                <Metric icon={Activity} label="Stability" value={`${percentFormatter.format(stability)}%`} />
                <Metric icon={CalendarDays} label="Window" value={`${monitoringDays} days`} />
                <Metric icon={GitBranch} label="Data points" value={numberFormatter.format(allPoints.length)} />
                <Metric icon={Clock3} label="Last sync" value={lastSync ? formatAxisDate(lastSync) : "Pending"} />
              </div>
            </section>
          </aside>
        </section>

        <section className="grid min-h-0 gap-4 xl:grid-cols-[1fr_1fr_360px]">
          <ActivityPanel
            title="New followers"
            items={newList}
            emptyText="No new followers in this watch window"
            tone="green"
            icon={UserPlus}
          />
          <ActivityPanel
            title="Lost followers"
            items={lostList}
            emptyText="No lost followers in this watch window"
            tone="rose"
            icon={UserMinus}
          />
          <section className="rounded-lg border border-[#30403a] bg-[#17201d] p-4 text-[#fffdf8] shadow-sm">
            <div className="flex items-start gap-3">
              <div className="rounded-lg border border-[#3f4a45] bg-[#25302c] p-2">
                <BarChart3 className="h-4 w-4 text-[#9be3c8]" />
              </div>
              <div>
                <h2 className="text-base font-semibold">Audience summary</h2>
                <p className="mt-1 text-xs leading-5 text-[#cbd7d1]">
                  {netChange === 0
                    ? "Follower count is steady across the selected view."
                    : `Follower count moved ${signedNumber(netChange)} across the selected view.`}
                </p>
                <div className="mt-3 flex items-center gap-2 text-xs text-[#cbd7d1]">
                  <CheckCircle2 className="h-4 w-4 text-[#9be3c8]" />
                  {latestPoint ? latestPoint.tooltipLabel : "Waiting for the first snapshot"}
                </div>
              </div>
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-0">
      <p className="flex items-center gap-1.5 text-[#66736d]">
        <Icon className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{label}</span>
      </p>
      <p className="mt-1 truncate font-semibold text-[#17201d]">{value}</p>
    </div>
  );
}
