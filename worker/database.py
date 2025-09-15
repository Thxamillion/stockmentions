import asyncio
import asyncpg
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import logging
from config import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                config.DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise

    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def ensure_tables_exist(self):
        """Ensure all required tables exist (for development)"""
        async with self.pool.acquire() as conn:
            # Check if mentions table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'mentions'
                );
            """)

            if not table_exists:
                logger.warning("Database tables don't exist. Please run the schema.sql file first.")

    async def insert_mention_batch(self, mentions: List[Dict]) -> int:
        """
        Insert a batch of mentions into the database
        Returns: Number of mentions actually inserted (excluding duplicates)
        """
        if not mentions:
            return 0

        async with self.pool.acquire() as conn:
            inserted_count = 0

            for mention in mentions:
                try:
                    await conn.execute("""
                        INSERT INTO mentions (
                            ticker, subreddit, post_id, comment_id, source,
                            created_at, author, context, reddit_created_utc, post_title
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        mention['ticker'],
                        mention['subreddit'],
                        mention['post_id'],
                        mention.get('comment_id'),
                        mention['source'],
                        mention['created_at'],
                        mention.get('author'),
                        mention.get('context'),
                        mention.get('reddit_created_utc'),
                        mention.get('post_title')
                    )
                    inserted_count += 1
                except asyncpg.UniqueViolationError:
                    # Skip duplicates
                    logger.debug(f"Duplicate mention skipped: {mention['ticker']} in {mention['post_id']}")
                    continue
                except Exception as e:
                    logger.error(f"Error inserting mention {mention}: {e}")
                    continue

            logger.info(f"Inserted {inserted_count} new mentions out of {len(mentions)} attempted")
            return inserted_count

    async def insert_dd_post(self, dd_post: Dict) -> bool:
        """
        Insert a due diligence post into the database
        Returns: True if inserted, False if duplicate or error
        """
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO due_diligence_posts (
                        post_id, ticker, title, content, subreddit, author,
                        created_at, upvotes, comments_count, quality_score,
                        dd_confidence, tags, post_url, reddit_created_utc,
                        has_charts, has_tables, word_count, sector
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                """,
                    dd_post['post_id'],
                    dd_post['ticker'],
                    dd_post['title'],
                    dd_post['content'],
                    dd_post['subreddit'],
                    dd_post.get('author'),
                    dd_post['created_at'],
                    dd_post.get('upvotes', 0),
                    dd_post.get('comments_count', 0),
                    dd_post.get('quality_score'),
                    dd_post.get('dd_confidence'),
                    dd_post.get('tags', []),
                    dd_post.get('post_url'),
                    dd_post.get('reddit_created_utc'),
                    dd_post.get('has_charts', False),
                    dd_post.get('has_tables', False),
                    dd_post.get('word_count'),
                    dd_post.get('sector')
                )
                logger.info(f"Inserted DD post: {dd_post['title'][:50]}...")
                return True
            except asyncpg.UniqueViolationError:
                logger.debug(f"Duplicate DD post skipped: {dd_post['post_id']}")
                return False
            except Exception as e:
                logger.error(f"Error inserting DD post {dd_post['post_id']}: {e}")
                return False

    async def get_recent_post_ids(self, subreddit: str, hours: int = 24) -> set:
        """Get set of post IDs we've already processed recently"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT post_id
                FROM mentions
                WHERE subreddit = $1
                AND created_at > NOW() - INTERVAL '%d hours'
            """ % hours, subreddit)

            return {row['post_id'] for row in rows}

    async def update_subreddit_stats(self, subreddit: str, mention_count: int):
        """Update subreddit statistics"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO subreddit_config (subreddit, last_processed, total_mentions)
                VALUES ($1, NOW(), $2)
                ON CONFLICT (subreddit)
                DO UPDATE SET
                    last_processed = NOW(),
                    total_mentions = subreddit_config.total_mentions + $2
            """, subreddit, mention_count)

    async def get_top_tickers(self,
                             time_range: str = 'day',
                             subreddit: Optional[str] = None,
                             limit: int = 10) -> List[Dict]:
        """Get top tickers for the specified time range"""

        time_intervals = {
            'day': '24 hours',
            'week': '7 days',
            'month': '30 days'
        }

        interval = time_intervals.get(time_range, '24 hours')

        async with self.pool.acquire() as conn:
            if subreddit:
                query = """
                    SELECT
                        ticker,
                        subreddit,
                        SUM(hits) as total,
                        SUM(posts) as posts,
                        SUM(comments) as comments,
                        AVG(avg_sentiment) as avg_sentiment
                    FROM mentions_hourly
                    WHERE bucket_hour >= NOW() - INTERVAL %s
                    AND subreddit = $1
                    GROUP BY ticker, subreddit
                    ORDER BY total DESC
                    LIMIT $2
                """ % f"'{interval}'"

                rows = await conn.fetch(query, subreddit, limit)
            else:
                query = """
                    SELECT
                        ticker,
                        SUM(hits) as total,
                        SUM(posts) as posts,
                        SUM(comments) as comments,
                        AVG(avg_sentiment) as avg_sentiment
                    FROM mentions_hourly
                    WHERE bucket_hour >= NOW() - INTERVAL %s
                    GROUP BY ticker
                    ORDER BY total DESC
                    LIMIT $1
                """ % f"'{interval}'"

                rows = await conn.fetch(query, limit)

            return [dict(row) for row in rows]

    async def get_dd_posts(self,
                          ticker: Optional[str] = None,
                          subreddit: Optional[str] = None,
                          limit: int = 20,
                          min_confidence: float = 0.7) -> List[Dict]:
        """Get due diligence posts with optional filtering"""

        async with self.pool.acquire() as conn:
            base_query = """
                SELECT
                    post_id, ticker, title, content, subreddit, author,
                    created_at, upvotes, comments_count, quality_score,
                    dd_confidence, tags, post_url, has_charts, has_tables,
                    word_count, sector
                FROM due_diligence_posts
                WHERE dd_confidence >= $1
            """

            params = [min_confidence]
            param_count = 1

            if ticker:
                param_count += 1
                base_query += f" AND ticker = ${param_count}"
                params.append(ticker)

            if subreddit:
                param_count += 1
                base_query += f" AND subreddit = ${param_count}"
                params.append(subreddit)

            param_count += 1
            base_query += f" ORDER BY created_at DESC LIMIT ${param_count}"
            params.append(limit)

            rows = await conn.fetch(base_query, *params)
            return [dict(row) for row in rows]

    async def refresh_materialized_views(self):
        """Refresh materialized views for better query performance"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mentions_hourly")
                logger.info("Materialized view mentions_hourly refreshed")
            except Exception as e:
                logger.error(f"Error refreshing materialized view: {e}")

    async def get_database_stats(self) -> Dict:
        """Get basic database statistics"""
        async with self.pool.acquire() as conn:
            stats = {}

            # Total mentions
            stats['total_mentions'] = await conn.fetchval("SELECT COUNT(*) FROM mentions")

            # Total DD posts
            stats['total_dd_posts'] = await conn.fetchval("SELECT COUNT(*) FROM due_diligence_posts")

            # Mentions today
            stats['mentions_today'] = await conn.fetchval("""
                SELECT COUNT(*) FROM mentions
                WHERE created_at >= CURRENT_DATE
            """)

            # DD posts today
            stats['dd_posts_today'] = await conn.fetchval("""
                SELECT COUNT(*) FROM due_diligence_posts
                WHERE created_at >= CURRENT_DATE
            """)

            # Active subreddits
            stats['active_subreddits'] = await conn.fetchval("""
                SELECT COUNT(DISTINCT subreddit) FROM mentions
                WHERE created_at >= NOW() - INTERVAL '7 days'
            """)

            return stats

# Global database manager instance
db = DatabaseManager()

async def init_database():
    """Initialize database connection"""
    await db.connect()
    await db.ensure_tables_exist()

async def close_database():
    """Close database connection"""
    await db.disconnect()

# Example usage
if __name__ == "__main__":
    async def test_database():
        await init_database()

        # Test database stats
        stats = await db.get_database_stats()
        print("Database stats:", stats)

        # Test getting top tickers
        top_tickers = await db.get_top_tickers('day', limit=5)
        print("Top tickers:", top_tickers)

        await close_database()

    asyncio.run(test_database())