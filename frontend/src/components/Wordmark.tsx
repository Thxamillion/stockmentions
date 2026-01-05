export function Wordmark() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative h-10 w-10 overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
        <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 gap-0.5 p-2">
          <div className="rounded-md bg-zinc-900 dark:bg-white" />
          <div className="rounded-md bg-zinc-200 dark:bg-zinc-800" />
          <div className="rounded-md bg-zinc-200 dark:bg-zinc-800" />
          <div className="rounded-md bg-zinc-900 dark:bg-white" />
        </div>
      </div>
      <div>
        <div className="text-lg font-extrabold tracking-tight text-zinc-900 dark:text-zinc-100">
          StockMentions
        </div>
        <div className="text-xs text-zinc-600 dark:text-zinc-400">
          Popular tickers across Reddit
        </div>
      </div>
    </div>
  );
}
