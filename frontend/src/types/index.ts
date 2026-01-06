export interface TickerMention {
  ticker: string;
  comments: number;
  threads: number;
}

export interface SubredditData {
  id: string;
  name: string;
  rows: TickerMention[];
}

export interface TrendingResponse {
  period: string;
  lastUpdated: string;
  subreddits: SubredditData[];
  all: TickerMention[];
}

export type TimeRange = "24h" | "7d" | "30d";

export interface TimeOption {
  key: TimeRange;
  label: string;
}

export interface Subreddit {
  id: string;
  name: string;
}
