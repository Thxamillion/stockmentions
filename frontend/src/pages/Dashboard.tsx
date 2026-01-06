import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { SegmentedControl, SkeletonTableCard, TableCard, Wordmark } from "../components";
import { useTrendingData, trendingKeys } from "../hooks";
import { getTrending } from "../api/client";
import type { TimeRange } from "../types";

const TIME_OPTIONS = [
  { key: "24h" as const, label: "24H" },
  { key: "7d" as const, label: "7D" },
  { key: "30d" as const, label: "30D" },
];

function formatUpdated(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function Dashboard() {
  const [timeKey, setTimeKey] = useState<TimeRange>("7d");
  const queryClient = useQueryClient();

  // Use React Query hook instead of manual useEffect
  const { data, isLoading, error } = useTrendingData(timeKey);

  // Prefetch all time ranges on mount for instant filter switching
  useEffect(() => {
    const timeRanges: TimeRange[] = ["24h", "7d", "30d"];

    timeRanges.forEach((range) => {
      queryClient.prefetchQuery({
        queryKey: trendingKeys.byTimeRange(range),
        queryFn: () => getTrending(range),
      });
    });
  }, [queryClient]);

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-black dark:text-zinc-100">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-6">
        {/* Header */}
        <header className="pt-6 pb-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <Wordmark />

            <div className="flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400">
              <span
                className="inline-flex h-2 w-2 rounded-full bg-emerald-500"
                aria-hidden="true"
              />
              <span>
                Last updated: {data ? formatUpdated(data.lastUpdated) : "Loading..."}
              </span>
            </div>
          </div>
        </header>

        {/* Sticky filter bar */}
        <div className="sticky top-0 z-20 -mx-4 sm:-mx-6 lg:-mx-6">
          <div className="bg-zinc-50/80 px-4 py-3 backdrop-blur dark:bg-black/70 sm:px-6 lg:px-6">
            <div className="rounded-2xl border border-zinc-200 bg-white px-3 py-3 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                    Time range
                  </div>
                  <div className="mt-1">
                    <SegmentedControl
                      value={timeKey}
                      onChange={setTimeKey}
                      options={TIME_OPTIONS}
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 sm:justify-end">
                  <div className="text-xs text-zinc-500 dark:text-zinc-400">
                    Tables show{" "}
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      Ticker
                    </span>
                    ,{" "}
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      # Comments
                    </span>
                    , and{" "}
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      # Threads
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Content */}
        <main className="pb-10 pt-4">
          {error ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
              <p className="font-semibold">Error loading data</p>
              <p className="mt-1">{error.message}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-2 rounded-lg bg-red-100 px-3 py-1 text-xs font-semibold hover:bg-red-200 dark:bg-red-900 dark:hover:bg-red-800"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => <SkeletonTableCard key={i} />)
              ) : data ? (
                <>
                  {/* All subreddits aggregated */}
                  <TableCard
                    title="All subreddits"
                    subtitle={`${timeKey.toUpperCase()} - Aggregated across communities`}
                    rows={data.all}
                  />

                  {/* Individual subreddit tables */}
                  {data.subreddits.map((sub) => (
                    <TableCard
                      key={sub.id}
                      title={sub.name}
                      subtitle={`${timeKey.toUpperCase()} - Top tickers in ${sub.name}`}
                      rows={sub.rows}
                    />
                  ))}
                </>
              ) : null}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
