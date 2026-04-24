"use client";

import { AlertTriangle, Brain, CheckCircle2, RefreshCw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { InsightMode, InsightRange, InsightResponse } from "@/lib/api";

const insightRanges: Array<{ key: InsightRange; label: string }> = [
  { key: "24h", label: "24h" },
  { key: "7d", label: "7D" },
  { key: "30d", label: "30D" },
];

const insightModes: Array<{ key: InsightMode; label: string }> = [
  { key: "brief", label: "Brief" },
  { key: "executive", label: "Executive" },
  { key: "technical", label: "Technical" },
];

function formatGeneratedAt(value: string | null) {
  if (!value) return "Not generated";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function confidenceClass(confidence: InsightResponse["confidence"]) {
  if (confidence === "high") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (confidence === "medium") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-rose-200 bg-rose-50 text-rose-700";
}

export function InsightsPanel({
  insight,
  mode,
  range,
  loading,
  error,
  onModeChange,
  onRangeChange,
  onGenerate,
}: {
  insight: InsightResponse | null;
  mode: InsightMode;
  range: InsightRange;
  loading: boolean;
  error: string | null;
  onModeChange: (mode: InsightMode) => void;
  onRangeChange: (range: InsightRange) => void;
  onGenerate: (refresh?: boolean) => void;
}) {
  return (
    <Card className="border-white/70 bg-white/95 shadow-[0_20px_45px_-30px_rgba(15,23,42,0.5)] backdrop-blur-sm">
      <CardHeader className="border-b border-slate-100 pb-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
              <Brain className="h-4 w-4" />
              AI insights
            </div>
            <CardTitle className="mt-2 text-xl tracking-tight">Grounded narrative</CardTitle>
            <CardDescription className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Generated from local dashboard metrics, follower events, annotations, and health state.
            </CardDescription>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-full border border-slate-200 bg-white p-1 shadow-sm">
              {insightRanges.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => onRangeChange(item.key)}
                  aria-pressed={range === item.key}
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                    range === item.key
                      ? "bg-slate-950 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="inline-flex rounded-full border border-slate-200 bg-white p-1 shadow-sm">
              {insightModes.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => onModeChange(item.key)}
                  aria-pressed={mode === item.key}
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                    mode === item.key
                      ? "bg-teal-700 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <Button size="sm" onClick={() => onGenerate(Boolean(insight))} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              {insight ? "Refresh insights" : "Generate brief"}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="grid gap-4 p-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
        <div className="grid gap-4">
          {error && (
            <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!insight && !loading && !error && (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-600">
              Generate a grounded readout for the selected range and mode.
            </div>
          )}

          {loading && (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-8 text-sm text-slate-600">
              Building a data-grounded summary from the cached dashboard payload...
            </div>
          )}

          {insight && (
            <div className="grid gap-4">
              <div className="rounded-2xl border border-teal-200 bg-teal-50/80 px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${confidenceClass(insight.confidence)}`}>
                    {insight.confidence === "high" ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                    {insight.confidence} confidence
                  </span>
                  {insight.stale && (
                    <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-700">
                      stale data
                    </span>
                  )}
                </div>
                <h3 className="mt-3 text-lg font-semibold tracking-tight text-slate-950">{insight.headline}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-700">{insight.summary}</p>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                {insight.bullets.map((bullet) => (
                  <div key={bullet} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-700">
                    {bullet}
                  </div>
                ))}
              </div>

              {insight.data_warnings.length > 0 && (
                <div className="grid gap-2">
                  {insight.data_warnings.map((warning) => (
                    <div key={warning} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
                      {warning}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="grid gap-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Generated</p>
            <p className="mt-2 text-sm font-semibold text-slate-950">{formatGeneratedAt(insight?.generated_at ?? null)}</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-teal-700" />
              <p className="text-sm font-semibold text-slate-950">Evidence</p>
            </div>
            <div className="mt-3 grid gap-2">
              {(insight?.evidence ?? []).slice(0, 7).map((item) => (
                <div key={`${item.label}-${item.value}`} className="flex items-start justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold text-slate-700">{item.label}</p>
                    <p className="truncate text-[11px] text-slate-500">{item.source}</p>
                  </div>
                  <p className="max-w-[150px] truncate text-right text-xs font-semibold text-slate-950">{item.value}</p>
                </div>
              ))}

              {!insight && <p className="text-sm text-slate-500">Evidence appears after generation.</p>}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-sm font-semibold text-slate-950">Recommended next actions</p>
            <ul className="mt-3 grid gap-2 text-sm leading-6 text-slate-600">
              {(insight?.recommended_actions ?? ["Generate insights to see next actions."]).map((action) => (
                <li key={action} className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">
                  {action}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
