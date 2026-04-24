"use client";

import Image from "next/image";
import { ArrowUpRight, Building2, CalendarDays, Download, FileJson, MapPin, Sparkles, Users, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { EnrichedChange } from "@/lib/api";

type SortKey = "newest" | "oldest" | "signal" | "followers" | "repos";

const sortOptions: Array<{ key: SortKey; label: string }> = [
  { key: "newest", label: "Newest" },
  { key: "oldest", label: "Oldest" },
  { key: "signal", label: "Signal" },
  { key: "followers", label: "Reach" },
  { key: "repos", label: "Repos" },
];

function formatTimestamp(value: string) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
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

function exportDrawerCsv(title: string, items: EnrichedChange[]) {
  const rows = [
    ["username", "name", "timestamp", "followers", "public_repos", "signal_score", "signal_label", "profile_url"],
    ...items.map((item) => [
      item.username,
      item.name ?? "",
      item.timestamp,
      String(item.followers),
      String(item.public_repos),
      String(item.signal_score),
      item.signal_label,
      item.html_url,
    ]),
  ];
  const csv = rows
    .map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(","))
    .join("\n");
  downloadFile(`${title.toLowerCase().replaceAll(" ", "-")}.csv`, csv, "text/csv;charset=utf-8");
}

function exportDrawerJson(title: string, items: EnrichedChange[]) {
  downloadFile(
    `${title.toLowerCase().replaceAll(" ", "-")}.json`,
    JSON.stringify(items, null, 2),
    "application/json;charset=utf-8",
  );
}

export function ChangeDrawer({
  open,
  title,
  subtitle,
  tone,
  items,
  sort,
  onSortChange,
  onClose,
}: {
  open: boolean;
  title: string;
  subtitle: string;
  tone: "emerald" | "rose" | "sky";
  items: EnrichedChange[];
  sort: SortKey;
  onSortChange: (value: SortKey) => void;
  onClose: () => void;
}) {
  if (!open) return null;

  const toneClasses = {
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
    rose: "border-rose-200 bg-rose-50 text-rose-700",
    sky: "border-sky-200 bg-sky-50 text-sky-700",
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/40 backdrop-blur-sm">
      <div className="flex h-full w-full max-w-2xl flex-col border-l border-white/70 bg-[#fcfbf7] shadow-2xl">
        <div className="border-b border-slate-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${toneClasses[tone]}`}>
                {subtitle}
              </div>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{title}</h2>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close drawer">
              <X className="h-5 w-5" />
            </Button>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {sortOptions.map((option) => (
              <button
                key={option.key}
                type="button"
                onClick={() => onSortChange(option.key)}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                  sort === option.key
                    ? "border-slate-950 bg-slate-950 text-white"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {option.label}
              </button>
            ))}

            <div className="ml-auto flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => exportDrawerCsv(title, items)}>
                <Download className="mr-2 h-4 w-4" />
                CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportDrawerJson(title, items)}>
                <FileJson className="mr-2 h-4 w-4" />
                JSON
              </Button>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {items.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white/80 px-6 py-12 text-center">
              <p className="text-base font-semibold text-slate-900">No events in this window</p>
              <p className="mt-2 text-sm text-slate-500">As new follower changes land, they will appear here with enrichment.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <article
                  key={`${item.username}-${item.timestamp}`}
                  className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-[0_12px_32px_-26px_rgba(15,23,42,0.5)]"
                >
                  <div className="flex items-start gap-4">
                    {item.avatar_url ? (
                      <Image
                        src={item.avatar_url}
                        alt={`${item.username} avatar`}
                        width={52}
                        height={52}
                        className="h-14 w-14 rounded-xl border border-slate-200 object-cover"
                      />
                    ) : (
                      <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-slate-200 bg-slate-100 text-slate-500">
                        <Users className="h-5 w-5" />
                      </div>
                    )}

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-base font-semibold text-slate-950">
                            {item.name || item.username}
                          </p>
                          <p className="truncate text-sm text-slate-500">@{item.username}</p>
                        </div>

                        <a
                          href={item.html_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
                        >
                          Profile
                          <ArrowUpRight className="h-3.5 w-3.5" />
                        </a>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${toneClasses[tone]}`}>
                          <Sparkles className="mr-1 inline h-3 w-3" />
                          {item.signal_label} {item.signal_score.toFixed(0)}
                        </span>
                        <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                          <Users className="mr-1 inline h-3 w-3" />
                          {item.followers.toLocaleString()} followers
                        </span>
                        <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                          {item.public_repos.toLocaleString()} repos
                        </span>
                      </div>

                      {item.bio && <p className="mt-3 text-sm leading-6 text-slate-600">{item.bio}</p>}

                      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-500">
                        <span className="inline-flex items-center gap-1.5">
                          <CalendarDays className="h-3.5 w-3.5" />
                          {formatTimestamp(item.timestamp)}
                        </span>
                        {item.company && (
                          <span className="inline-flex items-center gap-1.5">
                            <Building2 className="h-3.5 w-3.5" />
                            {item.company}
                          </span>
                        )}
                        {item.location && (
                          <span className="inline-flex items-center gap-1.5">
                            <MapPin className="h-3.5 w-3.5" />
                            {item.location}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
