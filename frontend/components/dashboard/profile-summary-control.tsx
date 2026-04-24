"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ProfileSummaryContext, ProfileSummaryResponse, ProfileSummarySubject } from "@/lib/api";
import { summarizeProfile } from "@/lib/api";

function confidenceClass(confidence: ProfileSummaryResponse["confidence"]) {
  if (confidence === "high") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (confidence === "medium") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-rose-200 bg-rose-50 text-rose-700";
}

function sourceClass(source: ProfileSummaryResponse["summary_source"]) {
  if (source === "openai") return "border-teal-200 bg-white text-teal-800";
  return "border-slate-200 bg-white text-slate-600";
}

export function ProfileSummaryControl({
  profile,
  eventType = "profile",
  compact = false,
  className = "",
}: {
  profile: ProfileSummarySubject;
  eventType?: ProfileSummaryContext;
  compact?: boolean;
  className?: string;
}) {
  const [summary, setSummary] = useState<ProfileSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSummarize() {
    setLoading(true);
    setError(null);

    try {
      const next = await summarizeProfile(profile, eventType);
      setSummary(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Profile summary is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`min-w-0 ${summary ? "w-full" : ""} ${className}`}>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleSummarize}
        disabled={loading}
        aria-label={`Summarize @${profile.username}`}
        className={`rounded-full border-teal-200 bg-white text-teal-800 hover:bg-teal-50 ${compact ? "h-8 px-3 text-xs" : ""}`}
      >
        {loading ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <Sparkles className="mr-2 h-3.5 w-3.5" />}
        {loading ? "Summarizing" : "Summarize"}
      </Button>

      {error && (
        <div className="mt-3 rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {summary && (
        <div
          data-testid="profile-summary-result"
          className="mt-3 rounded-2xl border border-teal-100 bg-teal-50/70 px-4 py-3 text-sm text-slate-700"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-teal-800">
              <Sparkles className="h-3.5 w-3.5" />
              Profile summary
            </div>
            <div className="flex flex-wrap gap-2">
              <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${sourceClass(summary.summary_source)}`}>
                {summary.summary_source === "openai" ? summary.model ?? "OpenAI" : "Local"}
              </span>
              <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${confidenceClass(summary.confidence)}`}>
                {summary.confidence} confidence
              </span>
            </div>
          </div>

          <p className="mt-3 font-semibold leading-6 text-slate-950">{summary.headline}</p>
          <p className="mt-2 leading-6">{summary.summary}</p>

          <div className="mt-3 grid gap-2">
            {summary.bullets.slice(0, compact ? 3 : 5).map((bullet) => (
              <div key={bullet} className="flex gap-2 text-xs leading-5 text-slate-600">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-700" />
                <span>{bullet}</span>
              </div>
            ))}
          </div>

          <div className="mt-3 rounded-xl border border-white/70 bg-white/75 px-3 py-2 text-xs leading-5 text-slate-700">
            <span className="font-semibold text-slate-950">Next action:</span> {summary.recommended_next_action}
          </div>

          {summary.data_warnings.length > 0 && (
            <div className="mt-3 flex gap-2 text-xs leading-5 text-slate-500">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
              <span>{summary.data_warnings[0]}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
