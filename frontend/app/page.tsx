"use client";

import Image from "next/image";
import type { ComponentType, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Copy,
  Download,
  ExternalLink,
  FileJson,
  Github,
  LayoutGrid,
  Radio,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UserMinus,
  UserPlus,
  Users,
} from "lucide-react";

import { ChartPanel, type DashboardChartAnnotation, type DashboardChartMode, type DashboardChartPoint } from "@/components/dashboard/chart-panel";
import { ChangeDrawer } from "@/components/dashboard/change-drawer";
import { InsightsPanel } from "@/components/dashboard/insights-panel";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { DashboardSkeleton } from "@/components/dashboard/loading";
import { ProfileSummaryControl } from "@/components/dashboard/profile-summary-control";
import { QueryPanel } from "@/components/dashboard/query-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardData, DashboardQueryResponse, EnrichedChange, InsightMode, InsightRange, InsightResponse } from "@/lib/api";
import { askDashboardQuestion, getDashboard, getInsights } from "@/lib/api";

type RangeKey = "7d" | "30d" | "all";
type DensityKey = "comfortable" | "compact";
type DrawerView = "new" | "lost" | "high-signal" | null;
type SortKey = "newest" | "oldest" | "signal" | "followers" | "repos";

type RawPoint = {
  raw: Date;
  timestamp: string;
  count: number;
  delta: number;
};

const ranges: Array<{ key: RangeKey; label: string }> = [
  { key: "7d", label: "7D" },
  { key: "30d", label: "30D" },
  { key: "all", label: "All" },
];

const chartModes: Array<{ key: DashboardChartMode; label: string }> = [
  { key: "cumulative", label: "Audience" },
  { key: "delta", label: "Delta" },
];

const densities: Array<{ key: DensityKey; label: string }> = [
  { key: "comfortable", label: "Focus" },
  { key: "compact", label: "Compact" },
];

const numberFormatter = new Intl.NumberFormat("en-US");
const percentFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
});

function formatShortDate(date: Date) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatTimeLabel(date: Date) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
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

function formatRelativeMinutes(minutes: number | null | undefined) {
  if (minutes === null || minutes === undefined) return "Unknown";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.round(minutes / 60)}h ago`;
  return `${Math.round(minutes / 1440)}d ago`;
}

function signedNumber(value: number) {
  if (value > 0) return `+${numberFormatter.format(value)}`;
  return numberFormatter.format(value);
}

function formatAxisLabel(date: Date, spanDays: number) {
  if (spanDays <= 1) return formatTimeLabel(date);
  if (spanDays <= 120) return formatShortDate(date);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "2-digit",
  }).format(date);
}

function pluralize(value: number, singular: string, plural = `${singular}s`) {
  return `${value} ${value === 1 ? singular : plural}`;
}

function averageOf(values: number[]) {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function standardDeviation(values: number[]) {
  if (values.length <= 1) return 0;
  const average = averageOf(values);
  const variance =
    values.reduce((sum, value) => sum + (value - average) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function roundToSingleDecimal(value: number) {
  return Math.round(value * 10) / 10;
}

function useLocalStorageState<T>(key: string, initialValue: T) {
  const [state, setState] = useState<T>(() => {
    if (typeof window === "undefined") return initialValue;
    const raw = window.localStorage.getItem(key);
    if (!raw) return initialValue;

    try {
      return JSON.parse(raw) as T;
    } catch {
      return initialValue;
    }
  });

  useEffect(() => {
    window.localStorage.setItem(key, JSON.stringify(state));
  }, [key, state]);

  return [state, setState] as const;
}

function sortChanges(items: EnrichedChange[], sort: SortKey) {
  return [...items].sort((left, right) => {
    if (sort === "oldest") {
      return new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime();
    }
    if (sort === "signal") {
      return right.signal_score - left.signal_score || right.followers - left.followers;
    }
    if (sort === "followers") {
      return right.followers - left.followers || right.signal_score - left.signal_score;
    }
    if (sort === "repos") {
      return right.public_repos - left.public_repos || right.signal_score - left.signal_score;
    }
    return new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime();
  });
}

function downloadFile(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function buildSnapshotText(dashboard: DashboardData) {
  return [
    `GitHub Follower Intelligence`,
    `Account: @${dashboard.profile.username}`,
    `Followers: ${dashboard.stats.total_followers}`,
    `Net 24h: ${signedNumber(dashboard.metrics.net_24h)}`,
    `Net 7d: ${signedNumber(dashboard.metrics.net_7d)}`,
    `Net 30d: ${signedNumber(dashboard.metrics.net_30d)}`,
    `Average daily growth: ${signedNumber(Math.round(dashboard.metrics.average_daily_growth * 10) / 10)}`,
    `Churn rate: ${percentFormatter.format(dashboard.metrics.churn_rate)}%`,
    `Volatility: ${percentFormatter.format(dashboard.metrics.volatility_score)}`,
    `Signal status: ${dashboard.health.api_status}`,
  ].join("\n");
}

function exportCsv(dashboard: DashboardData) {
  const rows = [
    [
      "type",
      "username",
      "name",
      "timestamp",
      "followers",
      "public_repos",
      "signal_score",
      "signal_label",
      "profile_url",
    ],
  ];

  for (const item of dashboard.all_new_followers) {
    rows.push([
      "new",
      item.username,
      item.name ?? "",
      item.timestamp,
      String(item.followers),
      String(item.public_repos),
      String(item.signal_score),
      item.signal_label,
      item.html_url,
    ]);
  }
  for (const item of dashboard.all_lost_followers) {
    rows.push([
      "lost",
      item.username,
      item.name ?? "",
      item.timestamp,
      String(item.followers),
      String(item.public_repos),
      String(item.signal_score),
      item.signal_label,
      item.html_url,
    ]);
  }

  const csv = rows
    .map((row) =>
      row
        .map((value) => `"${String(value).replaceAll('"', '""')}"`)
        .join(","),
    )
    .join("\n");
  downloadFile("github-follower-events.csv", csv, "text/csv;charset=utf-8");
}

function statusBadgeClass(status: DashboardData["health"]["api_status"]) {
  if (status === "healthy") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "degraded") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-rose-200 bg-rose-50 text-rose-700";
}

function toneForActivity(kind: "new" | "lost" | "signal") {
  if (kind === "new") return "emerald" as const;
  if (kind === "lost") return "rose" as const;
  return "sky" as const;
}

export default function Home() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<DrawerView>(null);
  const [copied, setCopied] = useState(false);
  const [range, setRange] = useLocalStorageState<RangeKey>("ghfc-range", "all");
  const [mode, setMode] = useLocalStorageState<DashboardChartMode>("ghfc-chart-mode", "cumulative");
  const [density, setDensity] = useLocalStorageState<DensityKey>("ghfc-density", "comfortable");
  const [showAnnotations, setShowAnnotations] = useLocalStorageState<boolean>("ghfc-annotations", true);
  const [drawerSort, setDrawerSort] = useLocalStorageState<SortKey>("ghfc-drawer-sort", "newest");
  const [insightRange, setInsightRange] = useLocalStorageState<InsightRange>("ghfc-insight-range", "30d");
  const [insightMode, setInsightMode] = useLocalStorageState<InsightMode>("ghfc-insight-mode", "brief");
  const [insightCache, setInsightCache] = useState<Record<string, InsightResponse>>({});
  const [insightLoading, setInsightLoading] = useState(false);
  const [insightError, setInsightError] = useState<string | null>(null);
  const [question, setQuestion] = useState("What changed this month?");
  const [queryResponse, setQueryResponse] = useState<DashboardQueryResponse | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);

  const loadDashboard = useCallback(async (refresh: boolean) => {
    setRequestError(null);
    setLoading(true);

    try {
      const next = await getDashboard(refresh);
      setDashboard(next);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "The dashboard API is unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadInsight = useCallback(async (refresh = false, rangeOverride?: InsightRange, modeOverride?: InsightMode) => {
    const nextRange = rangeOverride ?? insightRange;
    const nextMode = modeOverride ?? insightMode;
    const cacheKey = `${nextRange}:${nextMode}`;

    if (!refresh && insightCache[cacheKey]) {
      setInsightError(null);
      return;
    }

    setInsightLoading(true);
    setInsightError(null);

    try {
      const next = await getInsights(nextRange, nextMode, refresh);
      setInsightCache((current) => ({
        ...current,
        [cacheKey]: next,
      }));
    } catch (error) {
      setInsightError(error instanceof Error ? error.message : "Insights are unavailable.");
    } finally {
      setInsightLoading(false);
    }
  }, [insightCache, insightMode, insightRange]);

  const askQuestion = useCallback(async (questionOverride?: string) => {
    const nextQuestion = questionOverride ?? question;
    if (!nextQuestion.trim()) return;

    setQuestion(nextQuestion);
    setQueryLoading(true);
    setQueryError(null);

    try {
      const next = await askDashboardQuestion(nextQuestion.trim(), insightRange);
      setQueryResponse(next);
    } catch (error) {
      setQueryError(error instanceof Error ? error.message : "Dashboard query is unavailable.");
    } finally {
      setQueryLoading(false);
    }
  }, [insightRange, question]);

  useEffect(() => {
    void loadDashboard(false);
  }, [loadDashboard]);

  useEffect(() => {
    const nextRange: InsightRange = range === "7d" ? "7d" : "30d";
    setInsightRange(nextRange);
  }, [range, setInsightRange]);

  useEffect(() => {
    if (!dashboard) return;
    void loadInsight(false);
  }, [dashboard, insightMode, insightRange, loadInsight]);

  const rawPoints = useMemo<RawPoint[]>(() => {
    if (!dashboard) return [];

    return dashboard.trends.labels
      .map((label, index) => {
        const raw = new Date(label);
        const count = dashboard.trends.history[index] ?? 0;
        const previous = dashboard.trends.history[index - 1] ?? count;
        return {
          raw,
          timestamp: label,
          count,
          delta: count - previous,
        };
      })
      .filter((point) => !Number.isNaN(point.raw.getTime()));
  }, [dashboard]);

  const fullSpanDays = useMemo(() => {
    if (rawPoints.length <= 1) return rawPoints.length === 1 ? 1 : 0;
    const first = rawPoints[0].raw.getTime();
    const last = rawPoints[rawPoints.length - 1].raw.getTime();
    return Math.max(1, Math.ceil((last - first) / 86400000));
  }, [rawPoints]);

  const windowPoints = useMemo(() => {
    if (rawPoints.length === 0) return rawPoints;
    if (range === "all") return rawPoints;

    const latest = rawPoints[rawPoints.length - 1].raw.getTime();
    const days = range === "7d" ? 7 : 30;
    const cutoff = latest - days * 24 * 60 * 60 * 1000;
    const filtered = rawPoints.filter((point) => point.raw.getTime() >= cutoff);
    return filtered.length > 0 ? filtered : [rawPoints[rawPoints.length - 1]];
  }, [rawPoints, range]);

  const comparisonWindow = useMemo(() => {
    if (range === "all" || rawPoints.length === 0 || windowPoints.length < 2) return [] as RawPoint[];

    const currentStart = windowPoints[0].raw.getTime();
    const currentEnd = windowPoints[windowPoints.length - 1].raw.getTime();
    const currentDuration = Math.max(24 * 60 * 60 * 1000, currentEnd - currentStart);
    const compareStart = currentStart - currentDuration;

    const filtered = rawPoints.filter((point) => {
      const timestamp = point.raw.getTime();
      return timestamp >= compareStart && timestamp < currentStart;
    });

    return filtered.length >= 2 ? filtered : [];
  }, [range, rawPoints, windowPoints]);

  const windowSpanDays = useMemo(() => {
    if (windowPoints.length <= 1) return windowPoints.length === 1 ? 1 : 0;
    const first = windowPoints[0].raw.getTime();
    const last = windowPoints[windowPoints.length - 1].raw.getTime();
    return Math.max(1, Math.ceil((last - first) / 86400000));
  }, [windowPoints]);

  const selectedRangeDays = range === "all" ? null : range === "7d" ? 7 : 30;
  const rangeCutoff = useMemo(() => {
    if (selectedRangeDays === null || rawPoints.length === 0) return null;
    const latest = rawPoints[rawPoints.length - 1].raw.getTime();
    return latest - selectedRangeDays * 24 * 60 * 60 * 1000;
  }, [rawPoints, selectedRangeDays]);

  const filteredNewFollowers = useMemo(() => {
    if (rangeCutoff === null) return dashboard?.all_new_followers ?? [];
    return (dashboard?.all_new_followers ?? []).filter(
      (item) => new Date(item.timestamp).getTime() >= rangeCutoff,
    );
  }, [dashboard, rangeCutoff]);

  const filteredLostFollowers = useMemo(() => {
    if (rangeCutoff === null) return dashboard?.all_lost_followers ?? [];
    return (dashboard?.all_lost_followers ?? []).filter(
      (item) => new Date(item.timestamp).getTime() >= rangeCutoff,
    );
  }, [dashboard, rangeCutoff]);

  const rankedNewFollowers = useMemo(
    () => sortChanges(filteredNewFollowers, "signal"),
    [filteredNewFollowers],
  );

  const chartData = useMemo<DashboardChartPoint[]>(() => {
    const fallbackCount = dashboard?.stats.total_followers ?? 0;
    const source = windowPoints.length > 0 ? windowPoints : [{
      raw: new Date(),
      timestamp: new Date().toISOString(),
      count: fallbackCount,
      delta: 0,
    }];

    return source.map((point, index) => {
      const comparePoint =
        comparisonWindow.length > 0
          ? comparisonWindow[
              Math.round((index * (comparisonWindow.length - 1)) / Math.max(1, source.length - 1))
            ] ?? null
          : null;

      return {
        x: point.raw.getTime(),
        index,
        axisLabel: formatAxisLabel(point.raw, Math.max(windowSpanDays, 1)),
        tooltipLabel: formatFullDate(point.raw),
        currentCount: point.count,
        currentDelta: point.delta,
        compareCount: comparePoint?.count ?? null,
        compareDelta: comparePoint?.delta ?? null,
      };
    });
  }, [comparisonWindow, dashboard, windowPoints, windowSpanDays]);

  const chartAnnotations = useMemo<DashboardChartAnnotation[]>(() => {
    if (!dashboard) return [];
    const visibleTimes = windowPoints.map((point) => point.raw.getTime());

    return dashboard.annotations
      .map((annotation, index) => {
        const targetTime = new Date(annotation.timestamp).getTime();
        const pointIndex = visibleTimes.findIndex((time) => time === targetTime);
        if (pointIndex === -1) return null;
        return {
          key: `${annotation.kind}-${index}`,
          x: targetTime,
          kind: annotation.kind,
          label: annotation.label,
          value: annotation.value,
          magnitude: annotation.magnitude,
        };
      })
      .filter((annotation): annotation is DashboardChartAnnotation => annotation !== null);
  }, [dashboard, windowPoints]);

  const counts = chartData.map((point) => point.currentCount);
  const baseline = counts[0] ?? dashboard?.stats.total_followers ?? 0;
  const peak = counts.length > 0 ? Math.max(...counts) : dashboard?.stats.total_followers ?? 0;
  const low = counts.length > 0 ? Math.min(...counts) : dashboard?.stats.total_followers ?? 0;
  const average = counts.length > 0 ? Math.round(counts.reduce((sum, value) => sum + value, 0) / counts.length) : 0;
  const deltaValues = chartData.map((point) => point.currentDelta);
  const biggestGain = deltaValues.length > 0 ? Math.max(...deltaValues) : 0;
  const deepestLoss = deltaValues.length > 0 ? Math.min(...deltaValues) : 0;
  const averageDelta = deltaValues.length > 0
    ? deltaValues.reduce((sum, value) => sum + value, 0) / deltaValues.length
    : 0;
  const flatSnapshots = deltaValues.filter((value) => value === 0).length;
  const allVisibleCountsFlat = counts.length > 0 && counts.every((value) => value === counts[0]);
  const allVisibleDeltasFlat = deltaValues.length > 0 && deltaValues.every((value) => value === 0);
  const selectedNetChange = counts.length > 1 ? counts[counts.length - 1] - counts[0] : 0;
  const selectedStepChanges = windowPoints.slice(1).map((point, index) => point.count - windowPoints[index].count);
  const selectedAverageGrowth = roundToSingleDecimal(averageOf(selectedStepChanges));
  const selectedVolatilityScore = roundToSingleDecimal(
    Math.min(100, standardDeviation(selectedStepChanges) * 18),
  );
  const selectedStabilityScore = roundToSingleDecimal(Math.max(0, 100 - selectedVolatilityScore));
  const selectedChurnRate = roundToSingleDecimal(
    (filteredLostFollowers.length / Math.max(dashboard?.profile.followers ?? 0, 1)) * 100,
  );
  const selectedWindowLabel = range === "all" ? "All history" : range === "7d" ? "Last 7 days" : "Last 30 days";
  const selectedWindowDescription =
    range === "all" ? "the captured change window" : `the last ${selectedRangeDays} days`;
  const selectedChangeLabel =
    range === "all" ? "History change" : `${selectedRangeDays}-day change`;
  const selectedActivitySummary =
    range === "all"
      ? "captured in the tracked change window"
      : `tracked in the last ${selectedRangeDays} days`;
  const sparseCoverage =
    selectedRangeDays !== null &&
    windowSpanDays < Math.min(selectedRangeDays, 2) &&
    fullSpanDays > windowSpanDays;
  const windowHint =
    sparseCoverage
      ? `Only ${pluralize(Math.max(windowSpanDays, 1), "day")} of snapshots are available inside the selected ${selectedRangeDays}-day window. Use All to inspect the full imported history.`
      : range === "all"
        ? `${pluralize(rawPoints.length, "snapshot")} imported across ${pluralize(Math.max(fullSpanDays, 1), "day")}.`
        : null;
  const hasComparisonWindow = comparisonWindow.length >= 2;
  const chartNote =
    mode === "delta"
      ? allVisibleDeltasFlat
        ? "No snapshot-to-snapshot follower movement was recorded in this window."
        : windowHint
      : allVisibleCountsFlat
        ? "Follower count is flat across the selected window."
        : windowHint;
  const chartHeight = density === "compact" ? 290 : 370;
  const previewLimit = density === "compact" ? 2 : 4;
  const sidebarWidth = density === "compact" ? "xl:grid-cols-[minmax(0,1fr)_340px]" : "xl:grid-cols-[minmax(0,1fr)_380px]";
  const profileBioClass = density === "compact" ? "mt-3 text-sm leading-6 text-slate-600" : "mt-4 text-sm leading-7 text-slate-600";

  const sortedNew = useMemo(
    () => sortChanges(filteredNewFollowers, drawerSort),
    [drawerSort, filteredNewFollowers],
  );
  const sortedLost = useMemo(
    () => sortChanges(filteredLostFollowers, drawerSort),
    [drawerSort, filteredLostFollowers],
  );
  const sortedHighSignal = useMemo(
    () => sortChanges(rankedNewFollowers, drawerSort),
    [drawerSort, rankedNewFollowers],
  );

  const drawerItems = drawer === "new" ? sortedNew : drawer === "lost" ? sortedLost : sortedHighSignal;
  const drawerTitle =
    drawer === "new"
      ? "New follower events"
      : drawer === "lost"
        ? "Lost follower events"
        : "High-signal followers";
  const drawerSubtitle =
    drawer === "new" ? "Growth feed" : drawer === "lost" ? "Churn feed" : "Priority watch";
  const primaryStatTiles =
    mode === "cumulative"
      ? [
          { label: "Baseline", value: numberFormatter.format(baseline) },
          { label: "Peak", value: numberFormatter.format(peak) },
          { label: "Average", value: numberFormatter.format(average) },
          { label: "Low", value: numberFormatter.format(low) },
        ]
      : [
          { label: "Biggest gain", value: signedNumber(biggestGain) },
          { label: "Largest drop", value: signedNumber(deepestLoss) },
          { label: "Average delta", value: signedNumber(Math.round(averageDelta * 10) / 10) },
          { label: "Flat snaps", value: numberFormatter.format(flatSnapshots) },
        ];
  const activeInsight = insightCache[`${insightRange}:${insightMode}`] ?? null;

  const insightLines = useMemo(() => {
    if (!dashboard) return [];

    return [
      selectedNetChange === 0
        ? `Audience movement is flat across ${selectedWindowLabel.toLowerCase()}.`
        : `Audience moved ${signedNumber(selectedNetChange)} across ${selectedWindowLabel.toLowerCase()}.`,
      dashboard.health.stale_data
        ? `Snapshot freshness is degraded. Latest reliable sync was ${formatRelativeMinutes(dashboard.health.data_freshness_minutes)}.`
        : `Snapshot freshness is healthy at ${formatRelativeMinutes(dashboard.health.data_freshness_minutes)}.`,
      rankedNewFollowers.length > 0
        ? `Top ranked follower in view: @${rankedNewFollowers[0].username}.`
        : `No ranked new followers were recorded in ${selectedWindowDescription}.`,
      range === "all"
        ? `The current dataset spans ${pluralize(Math.max(fullSpanDays, 1), "day")} of historical snapshots.`
        : `The selected view covers ${pluralize(Math.max(windowSpanDays, 1), "day")} with ${pluralize(windowPoints.length, "snapshot")}.`,
    ];
  }, [
    dashboard,
    fullSpanDays,
    rankedNewFollowers,
    range,
    selectedNetChange,
    selectedWindowDescription,
    selectedWindowLabel,
    windowPoints.length,
    windowSpanDays,
  ]);

  async function handleCopySnapshot() {
    if (!dashboard) return;
    await navigator.clipboard.writeText(buildSnapshotText(dashboard));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  if (loading && !dashboard) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(15,118,110,0.12),_transparent_28%),linear-gradient(180deg,#f8fafc_0%,#f8f5ef_100%)] px-5 py-5 text-slate-950">
        <div className="mx-auto max-w-[1600px]">
          <DashboardSkeleton />
        </div>
      </main>
    );
  }

  if (!dashboard) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f8fafc_0%,#f8f5ef_100%)] p-6">
        <Card className="max-w-xl border-white/70 bg-white/90 shadow-xl">
          <CardHeader>
            <CardTitle>Dashboard unavailable</CardTitle>
            <CardDescription>{requestError || "The dashboard could not reach the API."}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void loadDashboard(true)}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  const profile = dashboard.profile;
  const health = dashboard.health;
  const metrics = dashboard.metrics;
  const summaryTone = health.api_status === "healthy" ? "text-emerald-700" : health.api_status === "degraded" ? "text-amber-700" : "text-rose-700";

  return (
    <>
      <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(15,118,110,0.14),_transparent_24%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.12),_transparent_20%),linear-gradient(180deg,#f8fafc_0%,#f7f3ea_100%)] text-slate-950">
        <header className="border-b border-white/70 bg-white/75 backdrop-blur-xl">
          <div className="mx-auto flex max-w-[1600px] flex-col gap-4 px-5 py-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-white shadow-lg shadow-slate-950/10">
                  <Github className="h-6 w-6" />
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
                      GitHub Follower Intelligence
                    </h1>
                    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${statusBadgeClass(health.api_status)}`}>
                      <Radio className="h-3.5 w-3.5" />
                      {health.api_status === "healthy"
                        ? "Live"
                        : health.api_status === "degraded"
                          ? "Degraded"
                          : "Recovery"}
                    </span>
                  </div>

                  <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
                    <span>@{profile.username}</span>
                    <span className="h-1 w-1 rounded-full bg-slate-300" />
                    <span className={`inline-flex items-center gap-1.5 ${summaryTone}`}>
                      {health.stale_data ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                      {health.stale_data ? "Stale snapshot" : "Live data"}
                    </span>
                    <span className="h-1 w-1 rounded-full bg-slate-300" />
                    <span>{formatFullDate(new Date(dashboard.generated_at))}</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 xl:justify-end">
                <SegmentControl
                  label="Range"
                  items={ranges}
                  value={range}
                  onChange={(value) => setRange(value)}
                />
                <SegmentControl
                  label="View"
                  items={chartModes}
                  value={mode}
                  onChange={(value) => setMode(value)}
                />
                <SegmentControl
                  label="Density"
                  items={densities}
                  value={density}
                  onChange={(value) => setDensity(value)}
                />

                <Button
                  variant={showAnnotations ? "default" : "outline"}
                  size="sm"
                  onClick={() => setShowAnnotations((value) => !value)}
                >
                  <Sparkles className="mr-2 h-4 w-4" />
                  Annotations
                </Button>

                <Button variant="outline" size="sm" onClick={() => void loadDashboard(true)}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Refresh
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportCsv(dashboard)}>
                  <Download className="mr-2 h-4 w-4" />
                  CSV
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    downloadFile(
                      "github-follower-dashboard.json",
                      JSON.stringify(dashboard, null, 2),
                      "application/json;charset=utf-8",
                    )
                  }
                >
                  <FileJson className="mr-2 h-4 w-4" />
                  JSON
                </Button>
                <Button variant="outline" size="sm" onClick={() => void handleCopySnapshot()}>
                  <Copy className="mr-2 h-4 w-4" />
                  {copied ? "Copied" : "Copy snapshot"}
                </Button>
              </div>
            </div>

            {(requestError || health.partial_data || health.stale_data) && (
              <div className={`rounded-2xl border px-4 py-3 text-sm ${
                requestError || health.api_status === "error"
                  ? "border-rose-200 bg-rose-50 text-rose-700"
                  : "border-amber-200 bg-amber-50 text-amber-700"
              }`}>
                {requestError
                  ? `Live refresh failed. Showing the last available snapshot. ${requestError}`
                  : health.last_error
                    ? `Partial data mode. Some live enrichment calls failed: ${health.last_error}`
                    : `Snapshot freshness is degraded. Latest reliable sync: ${formatRelativeMinutes(health.data_freshness_minutes)}.`}
              </div>
            )}
          </div>
        </header>

        <div className={`mx-auto flex max-w-[1600px] flex-col gap-4 ${density === "compact" ? "px-4 py-4" : "px-5 py-5"}`}>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label="Total followers"
              value={numberFormatter.format(dashboard.stats.total_followers)}
              detail={`${numberFormatter.format(metrics.following)} following across the account`}
              accent="sky"
              icon={Users}
            />
            <KpiCard
              label="Net movement"
              value={signedNumber(selectedNetChange)}
              detail={`${selectedWindowLabel} audience movement`}
              accent={selectedNetChange < 0 ? "rose" : "emerald"}
              icon={selectedNetChange < 0 ? ArrowDownRight : ArrowUpRight}
            />
            <KpiCard
              label="New followers"
              value={`+${numberFormatter.format(filteredNewFollowers.length)}`}
              detail={`${numberFormatter.format(filteredNewFollowers.length)} ${selectedActivitySummary}`}
              accent="emerald"
              icon={UserPlus}
            />
            <KpiCard
              label="Lost followers"
              value={`-${numberFormatter.format(filteredLostFollowers.length)}`}
              detail={`${numberFormatter.format(filteredLostFollowers.length)} ${selectedActivitySummary}`}
              accent="rose"
              icon={UserMinus}
            />
          </section>

          <QueryPanel
            question={question}
            range={insightRange}
            response={queryResponse}
            loading={queryLoading}
            error={queryError}
            onQuestionChange={setQuestion}
            onAsk={(nextQuestion) => void askQuestion(nextQuestion)}
          />

          <section data-testid="dashboard-investigation-grid" className={`grid gap-4 ${sidebarWidth}`}>
            <div className="grid content-start gap-4">
              <Card data-testid="chart-card" className="overflow-hidden border-white/70 bg-white/90 shadow-[0_20px_45px_-30px_rgba(15,23,42,0.55)] backdrop-blur-sm">
                <CardHeader className="border-b border-slate-100 pb-5">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div>
                      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
                        <TrendingUp className="h-4 w-4" />
                        Audience trajectory
                      </div>
                      <CardTitle className="mt-2 text-2xl tracking-tight">Follower growth</CardTitle>
                      <CardDescription className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                        {mode === "cumulative"
                          ? hasComparisonWindow
                            ? "Current audience versus the previous comparison window."
                            : "Follower count over the selected window."
                          : "Snapshot-to-snapshot movement, useful for spotting bursts and churn."}
                      </CardDescription>
                    </div>

                    <div className="flex flex-wrap gap-2 text-xs">
                      <Badge tone="emerald">{selectedWindowLabel}</Badge>
                      <Badge tone="sky">{pluralize(windowPoints.length, "pt")}</Badge>
                      <Badge tone="amber">{pluralize(Math.max(windowSpanDays, 1), "day")} span</Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className={density === "compact" ? "p-4" : "p-5"}>
                  <ChartPanel
                    data={chartData}
                    annotations={chartAnnotations}
                    mode={mode}
                    showAnnotations={showAnnotations}
                    height={chartHeight}
                    note={chartNote}
                  />

                  <div className="mt-4 grid gap-3 border-t border-slate-100 pt-4 md:grid-cols-4">
                    {primaryStatTiles.map((tile) => (
                      <MetricTile key={tile.label} label={tile.label} value={tile.value} />
                    ))}
                  </div>

                  <div className="mt-4 grid gap-3 border-t border-slate-100 pt-4 md:grid-cols-4">
                    <MetricTile label="Avg daily growth" value={signedNumber(selectedAverageGrowth)} />
                    <MetricTile label="Churn rate" value={`${percentFormatter.format(selectedChurnRate)}%`} />
                    <MetricTile label="Volatility" value={percentFormatter.format(selectedVolatilityScore)} />
                    <MetricTile label="Stability" value={`${percentFormatter.format(selectedStabilityScore)}%`} />
                  </div>
                </CardContent>
              </Card>

              <div className="grid gap-4 xl:grid-cols-2">
                <ActivityCard
                  title="New followers"
                  subtitle={range === "all" ? "Captured gains" : `${selectedRangeDays}-day gains`}
                  icon={UserPlus}
                  tone="new"
                  items={filteredNewFollowers.slice(0, previewLimit)}
                  summary={`${numberFormatter.format(filteredNewFollowers.length)} ${selectedActivitySummary}`}
                  onOpen={() => setDrawer("new")}
                />
                <ActivityCard
                  title="Lost followers"
                  subtitle={range === "all" ? "Captured churn" : `${selectedRangeDays}-day churn`}
                  icon={UserMinus}
                  tone="lost"
                  items={filteredLostFollowers.slice(0, previewLimit)}
                  summary={`${numberFormatter.format(filteredLostFollowers.length)} ${selectedActivitySummary}`}
                  onOpen={() => setDrawer("lost")}
                />
              </div>
            </div>

            <aside className="grid content-start gap-4">
              <Card className="border-white/70 bg-white/90 shadow-[0_18px_42px_-28px_rgba(15,23,42,0.55)] backdrop-blur-sm">
                <CardContent className={density === "compact" ? "p-4" : "p-5"}>
                  <div className="flex items-start gap-4">
                    {profile.avatar_url ? (
                      <Image
                        src={profile.avatar_url}
                        alt={`${profile.username} avatar`}
                        width={64}
                        height={64}
                        className="h-16 w-16 rounded-2xl border border-slate-200 object-cover"
                      />
                    ) : (
                      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200 bg-slate-100">
                        <Github className="h-6 w-6 text-slate-500" />
                      </div>
                    )}

                    <div className="min-w-0 flex-1">
                      <h2 className="truncate text-xl font-semibold tracking-tight text-slate-950">
                        {profile.name || profile.username}
                      </h2>
                      <p className="mt-1 truncate text-sm font-medium text-slate-600">@{profile.username}</p>
                      <a
                        href={profile.html_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 transition hover:text-teal-800"
                      >
                        View profile
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </div>
                  </div>

                  {profile.bio && <p className={profileBioClass}>{profile.bio}</p>}

                  <ProfileSummaryControl profile={profile} eventType="profile" compact className="mt-4" />

                  <div className="mt-4 grid grid-cols-2 gap-3 border-t border-slate-100 pt-4">
                    <MetricTile label="Repositories" value={numberFormatter.format(profile.public_repos)} />
                    <MetricTile label="Following" value={numberFormatter.format(profile.following)} />
                    <MetricTile label="Followers" value={numberFormatter.format(profile.followers)} />
                    <MetricTile label="Created" value={profile.created_at ? formatShortDate(new Date(profile.created_at)) : "Unknown"} />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-white/70 bg-white/90 shadow-[0_18px_42px_-28px_rgba(15,23,42,0.55)] backdrop-blur-sm">
                <CardHeader className="pb-4">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-teal-700" />
                    <CardTitle className="text-lg">Signal quality</CardTitle>
                  </div>
                  <CardDescription className="text-sm leading-6 text-slate-600">
                    Observability for the follower dataset and sync quality.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-3 px-6 pb-6">
                  <QualityRow icon={Activity} label="API status" value={health.api_status} />
                  <QualityRow icon={Clock3} label="Freshness" value={formatRelativeMinutes(health.data_freshness_minutes)} />
                  <QualityRow icon={RefreshCw} label="Cadence" value={health.expected_cadence_minutes ? `${health.expected_cadence_minutes} min` : "Adaptive"} />
                  <QualityRow icon={BarChart3} label="Missed snapshots" value={numberFormatter.format(health.missed_snapshots)} />
                  <QualityRow icon={LayoutGrid} label="Snapshot count" value={numberFormatter.format(health.snapshot_count)} />
                  <QualityRow icon={AlertTriangle} label="Partial data" value={health.partial_data ? "Yes" : "No"} />
                  <QualityRow
                    icon={CheckCircle2}
                    label="Last success"
                    value={health.last_successful_sync ? formatFullDate(new Date(health.last_successful_sync)) : "Pending"}
                  />
                  <QualityRow
                    icon={AlertTriangle}
                    label="Last failure"
                    value={health.last_failed_sync ? formatFullDate(new Date(health.last_failed_sync)) : "None recorded"}
                  />
                  <div className="rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-slate-950">Recent sync runs</p>
                      <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        {health.recent_sync_runs.length} runs
                      </span>
                    </div>
                    <div className="mt-3 grid gap-2">
                      {health.recent_sync_runs.slice(0, 4).map((run) => (
                        <div
                          key={`${run.timestamp}-${run.status}`}
                          className={`rounded-xl border px-3 py-2 text-xs ${
                            run.status === "success"
                              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                              : "border-rose-200 bg-rose-50 text-rose-800"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold">{run.status}</span>
                            <span>{formatShortDate(new Date(run.timestamp))}</span>
                          </div>
                          <p className="mt-1 text-[11px] opacity-80">
                            {run.follower_count !== null ? `${numberFormatter.format(run.follower_count)} followers` : "No count"} · +{run.new_count} / -{run.lost_count}
                          </p>
                        </div>
                      ))}
                      {health.recent_sync_runs.length === 0 && (
                        <p className="text-sm text-slate-500">No sync runs have been recorded yet.</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-emerald-100 bg-white/95 shadow-[0_18px_42px_-28px_rgba(15,23,42,0.45)] backdrop-blur-sm">
                <CardHeader className="pb-4">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-emerald-600" />
                    <CardTitle className="text-lg">High-signal followers</CardTitle>
                  </div>
                  <CardDescription className="text-sm leading-6 text-slate-600">
                    New followers ranked by reach, activity, profile completeness, and tenure in the selected view.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 px-6 pb-6">
                  {rankedNewFollowers.slice(0, 3).map((item) => (
                    <article
                      key={`${item.username}-${item.timestamp}`}
                      className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-slate-950">{item.name || item.username}</p>
                          <p className="truncate text-xs text-slate-600">@{item.username}</p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="text-sm font-semibold text-emerald-700">{item.signal_score.toFixed(0)}</p>
                          <p className="text-xs text-slate-600">{item.followers.toLocaleString()} reach</p>
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <ProfileSummaryControl profile={item} eventType="high-signal" compact />
                        <Button variant="ghost" size="sm" onClick={() => setDrawer("high-signal")} className="h-8 rounded-full px-3 text-xs">
                          Inspect
                          <ChevronRight className="ml-1.5 h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </article>
                  ))}

                  {rankedNewFollowers.length === 0 && (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
                      No ranked new followers were recorded in {selectedWindowDescription}.
                    </div>
                  )}

                  <Button variant="outline" className="w-full" onClick={() => setDrawer("high-signal")}>
                    Review ranked followers
                    <ChevronRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            </aside>
          </section>

          <InsightsPanel
            insight={activeInsight}
            mode={insightMode}
            range={insightRange}
            loading={insightLoading}
            error={insightError}
            onModeChange={setInsightMode}
            onRangeChange={setInsightRange}
            onGenerate={(refresh) => void loadInsight(refresh)}
          />

          <Card className="border-white/70 bg-white/90 shadow-[0_20px_45px_-30px_rgba(15,23,42,0.55)] backdrop-blur-sm">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-teal-700" />
                <CardTitle className="text-lg">Audience summary</CardTitle>
              </div>
              <CardDescription>
                A concise read on momentum, dataset health, and where the next review should focus.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 px-6 pb-6 lg:grid-cols-[1.4fr_1fr]">
              <div className="grid gap-3">
                {insightLines.map((line) => (
                  <div
                    key={line}
                    className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
                  >
                    {line}
                  </div>
                ))}
              </div>

              <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-1">
                <InsightStat
                  label={selectedChangeLabel}
                  value={signedNumber(selectedNetChange)}
                  tone={selectedNetChange >= 0 ? "emerald" : "rose"}
                />
                <InsightStat
                  label="Window churn"
                  value={`${filteredLostFollowers.length}`}
                  tone={filteredLostFollowers.length === 0 ? "sky" : "rose"}
                />
                <InsightStat
                  label="Health state"
                  value={health.api_status}
                  tone={health.api_status === "healthy" ? "emerald" : health.api_status === "degraded" ? "amber" : "rose"}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </main>

      <ChangeDrawer
        open={drawer !== null}
        title={drawerTitle}
        subtitle={drawerSubtitle}
        tone={drawer === "lost" ? toneForActivity("lost") : drawer === "high-signal" ? toneForActivity("signal") : toneForActivity("new")}
        items={drawerItems}
        sort={drawerSort}
        onSortChange={setDrawerSort}
        onClose={() => setDrawer(null)}
      />
    </>
  );
}

function SegmentControl<T extends string>({
  label,
  items,
  value,
  onChange,
}: {
  label: string;
  items: Array<{ key: T; label: string }>;
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="inline-flex rounded-full border border-slate-200 bg-white/80 p-1 shadow-sm">
      <span className="sr-only">{label}</span>
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          onClick={() => onChange(item.key)}
          aria-pressed={value === item.key}
          className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
            value === item.key
              ? "bg-slate-950 text-white"
              : "text-slate-500 hover:bg-slate-100 hover:text-slate-700"
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function Badge({
  children,
  tone,
}: {
  children: ReactNode;
  tone: "emerald" | "sky" | "amber";
}) {
  const classes = {
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
    sky: "border-sky-200 bg-sky-50 text-sky-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
  };

  return (
    <span className={`rounded-full border px-2.5 py-1 font-semibold ${classes[tone]}`}>
      {children}
    </span>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50/80 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold tracking-tight text-slate-950">{value}</p>
    </div>
  );
}

function QualityRow({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-3">
      <div className="flex min-w-0 items-center gap-2">
        <Icon className="h-4 w-4 shrink-0 text-slate-500" />
        <span className="truncate text-sm font-medium text-slate-600">{label}</span>
      </div>
      <span className="truncate text-sm font-semibold text-slate-950">{value}</span>
    </div>
  );
}

function ActivityCard({
  title,
  subtitle,
  icon: Icon,
  tone,
  items,
  summary,
  onOpen,
}: {
  title: string;
  subtitle: string;
  icon: ComponentType<{ className?: string }>;
  tone: "new" | "lost";
  items: EnrichedChange[];
  summary: string;
  onOpen: () => void;
}) {
  const toneClasses =
    tone === "new"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : "border-rose-200 bg-rose-50 text-rose-700";

  return (
    <Card className="border-white/70 bg-white/90 shadow-[0_18px_42px_-28px_rgba(15,23,42,0.55)] backdrop-blur-sm">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-lg">{title}</CardTitle>
            <CardDescription className="mt-1">{subtitle}</CardDescription>
          </div>
          <div className={`rounded-2xl border p-3 ${toneClasses}`}>
            <Icon className="h-4 w-4" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-6 pb-6">
        {items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center">
            <p className="text-sm font-semibold text-slate-900">No recent changes in this watch window</p>
            <p className="mt-1 text-sm text-slate-500">{summary}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <article
                key={`${item.username}-${item.timestamp}`}
                className="rounded-2xl border border-slate-100 bg-slate-50/80 px-4 py-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-950">{item.name || item.username}</p>
                    <p className="truncate text-xs text-slate-500">
                      @{item.username} • {formatFullDate(new Date(item.timestamp))}
                    </p>
                  </div>
                  <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${toneClasses}`}>
                    {item.signal_label}
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <ProfileSummaryControl profile={item} eventType={tone} compact />
                  <Button variant="ghost" size="sm" onClick={onOpen} className="h-8 rounded-full px-3 text-xs">
                    Inspect
                    <ChevronRight className="ml-1.5 h-3.5 w-3.5" />
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{summary}</p>
          <Button variant="ghost" size="sm" onClick={onOpen}>
            View all
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function InsightStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "emerald" | "rose" | "amber" | "sky";
}) {
  const classes = {
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
    rose: "border-rose-200 bg-rose-50 text-rose-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    sky: "border-sky-200 bg-sky-50 text-sky-700",
  };

  return (
    <div className={`rounded-2xl border px-4 py-3 ${classes[tone]}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] opacity-80">{label}</p>
      <p className="mt-2 text-lg font-semibold tracking-tight">{value}</p>
    </div>
  );
}
