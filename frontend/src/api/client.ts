import type { TimeRange, TrendingResponse, TickerMention } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

// Mock data generation for development
function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function seededRandom(seed: number): () => number {
  let t = seed >>> 0;
  return function () {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

const TICKERS_POOL = [
  "AAPL", "TSLA", "NVDA", "MSFT", "AMD", "AMZN", "META", "GOOGL",
  "PLTR", "SOFI", "SPY", "QQQ", "IREN", "RKLB", "COIN", "SMCI",
  "NFLX", "BABA", "DIS", "NIO", "INTC", "UBER", "SHOP", "SNOW",
];

const SUBREDDITS = [
  { id: "wallstreetbets", name: "r/wallstreetbets" },
  { id: "stocks", name: "r/stocks" },
  { id: "investing", name: "r/investing" },
  { id: "options", name: "r/options" },
  { id: "stockmarket", name: "r/stockmarket" },
];

function generateMockRows(subredditId: string, timeKey: TimeRange, limit = 12): TickerMention[] {
  const rand = seededRandom(hashString(`${subredditId}|${timeKey}`));

  const size = Math.min(limit, 8 + Math.floor(rand() * 8));
  const chosen = new Set<string>();
  while (chosen.size < size) {
    chosen.add(TICKERS_POOL[Math.floor(rand() * TICKERS_POOL.length)]);
  }

  const baseComments =
    subredditId === "wallstreetbets" ? 1400 :
    subredditId === "stocks" ? 520 :
    subredditId === "options" ? 420 :
    subredditId === "pennystocks" ? 380 : 320;

  const timeMultiplier =
    timeKey === "24h" ? 0.45 :
    timeKey === "7d" ? 1 :
    timeKey === "30d" ? 2.9 : 6.8;

  const rows = Array.from(chosen).map((ticker) => {
    const heavy = rand() ** 0.55;
    const comments = Math.max(5, Math.round(baseComments * timeMultiplier * (0.15 + heavy)));
    const threads = Math.max(1, Math.round((comments / (6 + rand() * 10)) * (0.8 + rand() * 0.6)));
    return { ticker, comments, threads };
  });

  rows.sort((a, b) => b.comments - a.comments);
  return rows;
}

function mergeRows(listOfRows: TickerMention[][], limit = 12): TickerMention[] {
  const map = new Map<string, TickerMention>();
  for (const rows of listOfRows) {
    for (const r of rows) {
      const prev = map.get(r.ticker) || { ticker: r.ticker, comments: 0, threads: 0 };
      prev.comments += r.comments;
      prev.threads += r.threads;
      map.set(r.ticker, prev);
    }
  }
  const merged = Array.from(map.values());
  merged.sort((a, b) => b.comments - a.comments);
  return merged.slice(0, limit);
}

export async function getTrending(timeRange: TimeRange): Promise<TrendingResponse> {
  // In production, this would call the real API
  if (API_BASE_URL) {
    const response = await fetch(`${API_BASE_URL}/trending?period=${timeRange}`);
    if (!response.ok) throw new Error("Failed to fetch trending data");
    return response.json();
  }

  // Mock data for development
  await new Promise((resolve) => setTimeout(resolve, 300));

  const subredditsData = SUBREDDITS.map((sub) => ({
    id: sub.id,
    name: sub.name,
    rows: generateMockRows(sub.id, timeRange),
  }));

  const allRows = mergeRows(subredditsData.map((s) => s.rows));

  return {
    period: timeRange,
    lastUpdated: new Date().toISOString(),
    subreddits: subredditsData,
    all: allRows,
  };
}

export async function getTickerDetail(symbol: string, period: TimeRange = "24h") {
  if (API_BASE_URL) {
    const response = await fetch(`${API_BASE_URL}/ticker/${symbol}?period=${period}`);
    if (!response.ok) throw new Error("Failed to fetch ticker data");
    return response.json();
  }

  // Mock response
  await new Promise((resolve) => setTimeout(resolve, 200));

  return {
    ticker: symbol,
    company_name: `${symbol} Inc.`,
    period,
    total_mentions: Math.floor(Math.random() * 500) + 50,
    by_subreddit: {
      wallstreetbets: Math.floor(Math.random() * 200),
      stocks: Math.floor(Math.random() * 100),
      investing: Math.floor(Math.random() * 80),
    },
    recent_posts: [],
  };
}

export async function getSubredditData(name: string, period: TimeRange = "24h") {
  if (API_BASE_URL) {
    const response = await fetch(`${API_BASE_URL}/subreddit/${name}?period=${period}`);
    if (!response.ok) throw new Error("Failed to fetch subreddit data");
    return response.json();
  }

  // Mock response
  await new Promise((resolve) => setTimeout(resolve, 200));

  return {
    subreddit: name,
    period,
    top_tickers: generateMockRows(name, period, 20),
  };
}
