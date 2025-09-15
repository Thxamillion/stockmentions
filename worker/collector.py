#!/usr/bin/env python3

import asyncio
import asyncpraw
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import List, Dict, Set
import traceback

from config import config
from ticker_extractor import TickerExtractor
from dd_detector import DDDetector
from database import db, init_database, close_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('collector.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RedditCollector:
    def __init__(self):
        self.reddit = None
        self.ticker_extractor = TickerExtractor()
        self.dd_detector = DDDetector()
        self.running = True
        self.processed_posts: Set[str] = set()

    async def initialize(self):
        """Initialize Reddit API connection and database"""
        try:
            # Initialize Reddit API
            self.reddit = asyncpraw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                user_agent=config.REDDIT_USER_AGENT
            )

            # Test Reddit connection
            await self.reddit.user.me()
            logger.info("Reddit API connection established")

            # Initialize database
            await init_database()
            logger.info("Database connection established")

        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise

    async def collect_from_subreddit(self, subreddit_name: str) -> Dict:
        """Collect posts and comments from a single subreddit"""
        try:
            subreddit = await self.reddit.subreddit(subreddit_name)
            stats = {
                'subreddit': subreddit_name,
                'posts_processed': 0,
                'comments_processed': 0,
                'mentions_found': 0,
                'dd_posts_found': 0
            }

            # Get recent post IDs to avoid reprocessing
            recent_posts = await db.get_recent_post_ids(subreddit_name, hours=6)

            mentions_batch = []
            dd_posts_batch = []

            # Process new posts
            async for post in subreddit.new(limit=config.MAX_POSTS_PER_FETCH):
                if post.id in recent_posts or post.id in self.processed_posts:
                    continue

                self.processed_posts.add(post.id)
                stats['posts_processed'] += 1

                # Extract tickers from post title and content
                post_text = f"{post.title} {post.selftext}"
                tickers = self.ticker_extractor.extract_tickers_with_context(post_text)

                for ticker_data in tickers:
                    mention = {
                        'ticker': ticker_data['ticker'],
                        'subreddit': subreddit_name,
                        'post_id': post.id,
                        'comment_id': None,
                        'source': 'post',
                        'created_at': datetime.now(timezone.utc),
                        'author': str(post.author) if post.author else None,
                        'context': ticker_data['context'][:200],  # Limit context length
                        'reddit_created_utc': datetime.fromtimestamp(post.created_utc, timezone.utc),
                        'post_title': post.title[:200]  # Limit title length
                    }
                    mentions_batch.append(mention)
                    stats['mentions_found'] += 1

                # Check if post is due diligence
                if post.selftext and len(post.selftext.split()) > 50:  # Only check substantial posts
                    dd_result = self.dd_detector.detect_dd(post.title, post.selftext, subreddit_name)

                    if dd_result['is_dd']:
                        # Extract primary ticker for DD post
                        primary_ticker = 'UNKNOWN'
                        if tickers:
                            primary_ticker = tickers[0]['ticker']  # Use first/highest confidence ticker

                        metadata = self.dd_detector.extract_dd_metadata(post.title, post.selftext)

                        dd_post = {
                            'post_id': post.id,
                            'ticker': primary_ticker,
                            'title': post.title[:500],  # Limit title length
                            'content': post.selftext[:5000],  # Limit content length for storage
                            'subreddit': subreddit_name,
                            'author': str(post.author) if post.author else None,
                            'created_at': datetime.now(timezone.utc),
                            'upvotes': post.score,
                            'comments_count': post.num_comments,
                            'quality_score': dd_result['score'],
                            'dd_confidence': dd_result['dd_confidence'],
                            'tags': metadata['tags'],
                            'post_url': f"https://reddit.com{post.permalink}",
                            'reddit_created_utc': datetime.fromtimestamp(post.created_utc, timezone.utc),
                            'has_charts': metadata['has_charts'],
                            'has_tables': metadata['has_tables'],
                            'word_count': metadata['word_count'],
                            'sector': None  # Could be enhanced with sector detection
                        }
                        dd_posts_batch.append(dd_post)
                        stats['dd_posts_found'] += 1

                        logger.info(f"DD detected: {post.title[:50]}... (score: {dd_result['score']})")

                # Rate limiting
                await asyncio.sleep(config.RATE_LIMIT_DELAY)

            # Process comments from recent posts (limited to avoid rate limits)
            comment_count = 0
            async for comment in subreddit.comments(limit=config.MAX_COMMENTS_PER_FETCH):
                if comment_count >= config.MAX_COMMENTS_PER_FETCH:
                    break

                if hasattr(comment, 'body') and comment.body:
                    tickers = self.ticker_extractor.extract_tickers_with_context(comment.body)

                    for ticker_data in tickers:
                        mention = {
                            'ticker': ticker_data['ticker'],
                            'subreddit': subreddit_name,
                            'post_id': comment.submission.id,
                            'comment_id': comment.id,
                            'source': 'comment',
                            'created_at': datetime.now(timezone.utc),
                            'author': str(comment.author) if comment.author else None,
                            'context': ticker_data['context'][:200],
                            'reddit_created_utc': datetime.fromtimestamp(comment.created_utc, timezone.utc),
                            'post_title': comment.submission.title[:200] if hasattr(comment.submission, 'title') else None
                        }
                        mentions_batch.append(mention)
                        stats['mentions_found'] += 1

                comment_count += 1
                stats['comments_processed'] += 1

                # Rate limiting
                await asyncio.sleep(config.RATE_LIMIT_DELAY)

            # Batch insert mentions
            if mentions_batch:
                inserted = await db.insert_mention_batch(mentions_batch)
                logger.info(f"{subreddit_name}: Inserted {inserted} mentions")

            # Insert DD posts
            for dd_post in dd_posts_batch:
                await db.insert_dd_post(dd_post)

            # Update subreddit stats
            await db.update_subreddit_stats(subreddit_name, len(mentions_batch))

            return stats

        except Exception as e:
            logger.error(f"Error collecting from r/{subreddit_name}: {e}")
            logger.error(traceback.format_exc())
            return {
                'subreddit': subreddit_name,
                'posts_processed': 0,
                'comments_processed': 0,
                'mentions_found': 0,
                'dd_posts_found': 0,
                'error': str(e)
            }

    async def run_collection_cycle(self):
        """Run one complete collection cycle across all subreddits"""
        logger.info("Starting collection cycle...")
        total_stats = {
            'cycle_start': datetime.now(timezone.utc),
            'subreddits_processed': 0,
            'total_posts': 0,
            'total_comments': 0,
            'total_mentions': 0,
            'total_dd_posts': 0
        }

        for subreddit_name in config.SUBREDDITS:
            try:
                logger.info(f"Processing r/{subreddit_name}...")
                stats = await self.collect_from_subreddit(subreddit_name)

                total_stats['subreddits_processed'] += 1
                total_stats['total_posts'] += stats['posts_processed']
                total_stats['total_comments'] += stats['comments_processed']
                total_stats['total_mentions'] += stats['mentions_found']
                total_stats['total_dd_posts'] += stats['dd_posts_found']

                logger.info(f"r/{subreddit_name} completed: "
                           f"{stats['posts_processed']} posts, "
                           f"{stats['comments_processed']} comments, "
                           f"{stats['mentions_found']} mentions, "
                           f"{stats['dd_posts_found']} DD posts")

            except Exception as e:
                logger.error(f"Failed to process r/{subreddit_name}: {e}")

        # Refresh materialized views periodically
        current_hour = datetime.now().hour
        if current_hour % 2 == 0:  # Every 2 hours
            await db.refresh_materialized_views()

        total_stats['cycle_end'] = datetime.now(timezone.utc)
        duration = (total_stats['cycle_end'] - total_stats['cycle_start']).total_seconds()

        logger.info(f"Collection cycle completed in {duration:.1f}s: "
                   f"{total_stats['total_mentions']} mentions, "
                   f"{total_stats['total_dd_posts']} DD posts found")

        return total_stats

    async def run(self):
        """Main run loop"""
        logger.info("StockMentions Reddit Collector starting...")

        try:
            await self.initialize()

            cycle_count = 0
            while self.running:
                cycle_count += 1
                logger.info(f"--- Cycle {cycle_count} ---")

                try:
                    await self.run_collection_cycle()
                except Exception as e:
                    logger.error(f"Error in collection cycle: {e}")
                    logger.error(traceback.format_exc())

                if self.running:
                    logger.info(f"Waiting {config.WORKER_INTERVAL_SECONDS} seconds until next cycle...")
                    await asyncio.sleep(config.WORKER_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.error(traceback.format_exc())
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up...")
        if self.reddit:
            await self.reddit.close()
        await close_database()
        logger.info("Cleanup completed")

    def stop(self):
        """Stop the collector"""
        logger.info("Stop signal received")
        self.running = False

# Signal handlers
collector = None

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}")
    if collector:
        collector.stop()

async def main():
    global collector

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Validate configuration
    if not config.REDDIT_CLIENT_ID or not config.REDDIT_CLIENT_SECRET:
        logger.error("Reddit API credentials not configured. Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
        sys.exit(1)

    # Start collector
    collector = RedditCollector()
    await collector.run()

if __name__ == "__main__":
    asyncio.run(main())