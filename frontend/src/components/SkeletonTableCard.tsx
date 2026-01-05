export function SkeletonTableCard() {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="h-4 w-36 rounded bg-zinc-200 dark:bg-zinc-800 animate-pulse" />
          <div className="h-3 w-44 rounded bg-zinc-100 dark:bg-zinc-900 animate-pulse" />
        </div>
        <div className="h-7 w-16 rounded-lg bg-zinc-100 dark:bg-zinc-900 animate-pulse" />
      </div>
      <div className="mt-4 space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-8 w-full rounded-xl bg-zinc-100 dark:bg-zinc-900 animate-pulse" />
        ))}
      </div>
    </div>
  );
}
