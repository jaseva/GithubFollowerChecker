import type { ComponentType } from "react";

import { Card, CardContent } from "@/components/ui/card";

export function KpiCard({
  label,
  value,
  detail,
  accent,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail: string;
  accent: "emerald" | "rose" | "sky" | "amber";
  icon: ComponentType<{ className?: string }>;
}) {
  const accents = {
    emerald: {
      badge: "border-emerald-200 bg-emerald-50 text-emerald-700",
      glow: "from-emerald-100/70 via-transparent to-transparent",
    },
    rose: {
      badge: "border-rose-200 bg-rose-50 text-rose-700",
      glow: "from-rose-100/70 via-transparent to-transparent",
    },
    sky: {
      badge: "border-sky-200 bg-sky-50 text-sky-700",
      glow: "from-sky-100/70 via-transparent to-transparent",
    },
    amber: {
      badge: "border-amber-200 bg-amber-50 text-amber-700",
      glow: "from-amber-100/70 via-transparent to-transparent",
    },
  };

  return (
    <Card className="relative overflow-hidden border-white/70 bg-white/90 shadow-[0_12px_40px_-24px_rgba(15,23,42,0.45)] backdrop-blur-sm">
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${accents[accent].glow}`} />
      <CardContent className="flex h-full items-start justify-between gap-4 p-5">
        <div className="min-w-0">
          <p className="truncate text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {label}
          </p>
          <p className="mt-3 truncate text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
          <p className="mt-3 truncate text-sm text-slate-500">{detail}</p>
        </div>

        <div className={`rounded-xl border p-3 shadow-sm ${accents[accent].badge}`}>
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}
