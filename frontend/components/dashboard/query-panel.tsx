"use client";

import { AlertTriangle, CornerDownLeft, MessageSquareText, Search, Sparkles } from "lucide-react";
import { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardQueryResponse, InsightRange } from "@/lib/api";

const exampleQuestions = [
  "What changed this month?",
  "Who are the most important new followers?",
  "When did churn spike?",
  "Summarize the last 30 days for a manager.",
];

function confidenceClass(confidence: DashboardQueryResponse["confidence"]) {
  if (confidence === "high") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (confidence === "medium") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-rose-200 bg-rose-50 text-rose-700";
}

export function QueryPanel({
  question,
  range,
  response,
  loading,
  error,
  onQuestionChange,
  onAsk,
}: {
  question: string;
  range: InsightRange;
  response: DashboardQueryResponse | null;
  loading: boolean;
  error: string | null;
  onQuestionChange: (question: string) => void;
  onAsk: (question?: string) => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onAsk();
  }

  return (
    <Card className="border-white/70 bg-white/95 shadow-[0_20px_45px_-30px_rgba(15,23,42,0.5)] backdrop-blur-sm">
      <CardHeader className="pb-4">
        <div className="flex items-center gap-2">
          <MessageSquareText className="h-4 w-4 text-teal-700" />
          <CardTitle className="text-lg">Ask the dashboard</CardTitle>
        </div>
        <CardDescription className="text-sm leading-6 text-slate-600">
          Answers use local dashboard data only and return inspectable evidence.
        </CardDescription>
      </CardHeader>

      <CardContent className="grid gap-4 px-6 pb-6">
        <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
          <label className="sr-only" htmlFor="dashboard-question">
            Dashboard question
          </label>
          <div className="flex min-w-0 flex-1 items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-100">
            <Search className="h-4 w-4 shrink-0 text-slate-500" />
            <input
              id="dashboard-question"
              value={question}
              onChange={(event) => onQuestionChange(event.target.value)}
              placeholder="Ask about churn, high-signal followers, movement, or data health"
              className="min-w-0 flex-1 bg-transparent text-sm text-slate-950 outline-none placeholder:text-slate-400"
            />
          </div>
          <Button type="submit" disabled={loading || question.trim().length === 0}>
            <CornerDownLeft className="mr-2 h-4 w-4" />
            Ask
          </Button>
        </form>

        <div className="flex flex-wrap gap-2">
          {exampleQuestions.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => onAsk(example)}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:border-teal-200 hover:bg-teal-50 hover:text-teal-700"
            >
              {example}
            </button>
          ))}
        </div>

        {error && (
          <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {loading && (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-600">
            Answering from cached dashboard data for the {range} window...
          </div>
        )}

        {response && !loading && (
          <div className="grid gap-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-700">
                  {response.interpreted_intent.replaceAll("_", " ")}
                </span>
                <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${confidenceClass(response.confidence)}`}>
                  {response.confidence} confidence
                </span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-800">{response.answer}</p>
              <div className="mt-3 rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-medium text-teal-800">
                {response.recommended_next_action}
              </div>
            </div>

            <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-teal-700" />
                  <p className="text-sm font-semibold text-slate-950">Evidence</p>
                </div>
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  {response.evidence.slice(0, 6).map((item) => (
                    <div key={`${item.label}-${item.value}`} className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-xs font-semibold text-slate-700">{item.label}</p>
                        <p className="text-right text-xs font-semibold text-slate-950">{item.value}</p>
                      </div>
                      <p className="mt-1 truncate text-[11px] text-slate-500">{item.source}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <p className="text-sm font-semibold text-slate-950">Trust notes</p>
                <div className="mt-3 grid gap-2">
                  {response.data_warnings.length > 0 ? (
                    response.data_warnings.map((warning) => (
                      <div key={warning} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
                        {warning}
                      </div>
                    ))
                  ) : (
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-800">
                      No data quality warnings were raised for this answer.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
