import type { TickerMention } from "../types";

function formatInt(n: number): string {
  return new Intl.NumberFormat().format(Math.round(n));
}

interface TableCardProps {
  title: string;
  subtitle: string;
  rows: TickerMention[];
}

export function TableCard({ title, subtitle, rows }: TableCardProps) {
  const totalComments = rows.reduce((a, b) => a + b.comments, 0);
  const totalThreads = rows.reduce((a, b) => a + b.threads, 0);

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="min-w-0">
        <h3 className="truncate text-base font-bold text-zinc-900 dark:text-zinc-100">
          {title}
        </h3>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{subtitle}</p>
      </div>

      <div className="mt-4 overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
              <tr>
                <th scope="col" className="px-3 py-2">
                  Ticker
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Comments
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Threads
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
              {rows.map((r) => (
                <tr
                  key={r.ticker}
                  className="hover:bg-zinc-50 dark:hover:bg-zinc-900/60"
                >
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-zinc-100 text-xs font-bold text-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
                        {r.ticker[0]}
                      </span>
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                        {r.ticker}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right font-semibold text-zinc-900 dark:text-zinc-100">
                    {formatInt(r.comments)}
                  </td>
                  <td className="px-3 py-2 text-right text-zinc-700 dark:text-zinc-200">
                    {formatInt(r.threads)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
        <span>
          Total comments:{" "}
          <span className="font-semibold text-zinc-900 dark:text-zinc-100">
            {formatInt(totalComments)}
          </span>
        </span>
        <span>
          Total threads:{" "}
          <span className="font-semibold text-zinc-900 dark:text-zinc-100">
            {formatInt(totalThreads)}
          </span>
        </span>
      </div>
    </div>
  );
}
