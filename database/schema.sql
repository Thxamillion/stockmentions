-- StockMentions Database Schema
-- Target: Railway Postgres or any Postgres 14+

-- Core mentions table - stores all ticker mentions from Reddit
CREATE TABLE IF NOT EXISTS mentions (
  id BIGSERIAL PRIMARY KEY,
  ticker VARCHAR(10) NOT NULL,
  subreddit VARCHAR(50) NOT NULL,
  post_id VARCHAR(20) NOT NULL,
  comment_id VARCHAR(20), -- NULL for posts, populated for comments
  source VARCHAR(10) NOT NULL CHECK (source IN ('post', 'comment')),
  created_at TIMESTAMPTZ NOT NULL,
  author VARCHAR(50),
  context TEXT, -- Surrounding text for the mention
  sentiment_score DECIMAL(3,2), -- -1.0 to 1.0 (optional sentiment analysis)
  reddit_created_utc TIMESTAMPTZ, -- Original Reddit timestamp
  post_title TEXT, -- For comments, this is the parent post title
  UNIQUE(ticker, post_id, comment_id)
);

-- Due diligence posts - filtered and classified from mentions
CREATE TABLE IF NOT EXISTS due_diligence_posts (
  id BIGSERIAL PRIMARY KEY,
  post_id VARCHAR(20) UNIQUE NOT NULL,
  ticker VARCHAR(10) NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  subreddit VARCHAR(50) NOT NULL,
  author VARCHAR(50),
  created_at TIMESTAMPTZ NOT NULL,
  upvotes INTEGER DEFAULT 0,
  comments_count INTEGER DEFAULT 0,
  quality_score DECIMAL(3,1), -- 1.0 to 10.0 based on length, engagement, keywords
  dd_confidence DECIMAL(3,2), -- 0.0 to 1.0 - how confident we are this is DD
  tags TEXT[], -- ['Valuation', 'DCF', 'Thesis', 'Earnings', 'Risk Analysis']
  post_url TEXT,
  reddit_created_utc TIMESTAMPTZ,
  processed_at TIMESTAMPTZ DEFAULT NOW(),
  has_charts BOOLEAN DEFAULT FALSE,
  has_tables BOOLEAN DEFAULT FALSE,
  word_count INTEGER,
  sector VARCHAR(50) -- Auto-detected or manually tagged
);

-- Materialized view for fast ticker ranking queries
CREATE MATERIALIZED VIEW IF NOT EXISTS mentions_hourly AS
SELECT
  ticker,
  subreddit,
  DATE_TRUNC('hour', created_at) as bucket_hour,
  COUNT(*) as hits,
  SUM(CASE WHEN source = 'post' THEN 1 ELSE 0 END) as posts,
  SUM(CASE WHEN source = 'comment' THEN 1 ELSE 0 END) as comments,
  AVG(sentiment_score) as avg_sentiment
FROM mentions
WHERE created_at >= NOW() - INTERVAL '90 days' -- Only last 90 days
GROUP BY ticker, subreddit, bucket_hour;

-- Ticker reference table (optional - for validation)
CREATE TABLE IF NOT EXISTS tickers_reference (
  ticker VARCHAR(10) PRIMARY KEY,
  company_name TEXT,
  sector VARCHAR(50),
  market_cap BIGINT,
  exchange VARCHAR(10), -- NYSE, NASDAQ, etc
  is_active BOOLEAN DEFAULT TRUE,
  added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subreddit configuration
CREATE TABLE IF NOT EXISTS subreddit_config (
  subreddit VARCHAR(50) PRIMARY KEY,
  is_active BOOLEAN DEFAULT TRUE,
  dd_weight DECIMAL(3,2) DEFAULT 1.0, -- Weight for DD detection
  last_processed TIMESTAMPTZ,
  total_mentions INTEGER DEFAULT 0
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_mentions_created ON mentions(created_at);
CREATE INDEX IF NOT EXISTS idx_mentions_ticker ON mentions(ticker);
CREATE INDEX IF NOT EXISTS idx_mentions_subreddit ON mentions(subreddit);
CREATE INDEX IF NOT EXISTS idx_mentions_source ON mentions(source);
CREATE INDEX IF NOT EXISTS idx_mentions_ticker_created ON mentions(ticker, created_at);

CREATE INDEX IF NOT EXISTS idx_dd_ticker ON due_diligence_posts(ticker);
CREATE INDEX IF NOT EXISTS idx_dd_created ON due_diligence_posts(created_at);
CREATE INDEX IF NOT EXISTS idx_dd_quality ON due_diligence_posts(quality_score);
CREATE INDEX IF NOT EXISTS idx_dd_confidence ON due_diligence_posts(dd_confidence);
CREATE INDEX IF NOT EXISTS idx_dd_subreddit ON due_diligence_posts(subreddit);
CREATE INDEX IF NOT EXISTS idx_dd_tags ON due_diligence_posts USING GIN(tags);

CREATE INDEX IF NOT EXISTS idx_mentions_hourly_ticker ON mentions_hourly(ticker);
CREATE INDEX IF NOT EXISTS idx_mentions_hourly_bucket ON mentions_hourly(bucket_hour);

-- Seed some initial subreddit configuration
INSERT INTO subreddit_config (subreddit, is_active, dd_weight) VALUES
  ('stocks', TRUE, 1.0),
  ('investing', TRUE, 1.2),
  ('SecurityAnalysis', TRUE, 2.0),
  ('ValueInvesting', TRUE, 1.8),
  ('pennystocks', TRUE, 0.8),
  ('wallstreetbets', TRUE, 0.5),
  ('StockMarket', TRUE, 1.0),
  ('financialindependence', TRUE, 1.1),
  ('dividends', TRUE, 1.1)
ON CONFLICT (subreddit) DO NOTHING;