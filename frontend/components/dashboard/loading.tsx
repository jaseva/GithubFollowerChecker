export function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-32 animate-pulse rounded-xl border border-slate-200 bg-white/80"
          />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="h-[520px] animate-pulse rounded-xl border border-slate-200 bg-white/80" />
        <div className="grid gap-4">
          <div className="h-60 animate-pulse rounded-xl border border-slate-200 bg-white/80" />
          <div className="h-52 animate-pulse rounded-xl border border-slate-200 bg-white/80" />
          <div className="h-44 animate-pulse rounded-xl border border-slate-200 bg-white/80" />
        </div>
      </div>
    </div>
  );
}
