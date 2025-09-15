-- Refresh script for materialized views
-- Run this hourly via cron or application scheduler

REFRESH MATERIALIZED VIEW CONCURRENTLY mentions_hourly;

-- Optional: Clean up old data (run daily)
-- DELETE FROM mentions WHERE created_at < NOW() - INTERVAL '180 days';
-- DELETE FROM due_diligence_posts WHERE created_at < NOW() - INTERVAL '365 days';

-- Update subreddit stats (run daily)
UPDATE subreddit_config
SET total_mentions = (
  SELECT COUNT(*)
  FROM mentions
  WHERE mentions.subreddit = subreddit_config.subreddit
  AND created_at >= NOW() - INTERVAL '30 days'
);