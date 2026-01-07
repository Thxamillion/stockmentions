#!/usr/bin/env python3
"""
EC2 Worker for Stock Mentions
Fetches Reddit posts with ALL comments and stores ticker mentions in DynamoDB.

Usage:
  python worker.py              # Single run
  python worker.py --daemon     # Continuous daemon mode (loops with sleep)
  python worker.py --backfill   # Fetch more historical posts (limit=500)
"""

import os
import re
import sys
import time
import argparse
import logging
from datetime import datetime, timezone
from typing import Set, List, Dict, Any, Optional

import boto3
import praw
from botocore.config import Config

# ============================================================================
# Configuration
# ============================================================================

# AWS Region (can be overridden with AWS_REGION env var)
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# DynamoDB table names
STOCKS_TABLE = os.environ.get('STOCKS_TABLE', 'stock-mentions-stocks')
MENTIONS_TABLE = os.environ.get('MENTIONS_TABLE', 'stock-mentions-mentions')
METADATA_TABLE = os.environ.get('METADATA_TABLE', 'stock-mentions-metadata')

# Reddit credentials (from environment or SSM)
# If not set, will fetch from SSM Parameter Store
REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')
SSM_CLIENT_ID_PARAM = os.environ.get('SSM_CLIENT_ID_PARAM', '/stock-mentions/reddit_client_id')
SSM_CLIENT_SECRET_PARAM = os.environ.get('SSM_CLIENT_SECRET_PARAM', '/stock-mentions/reddit_client_secret')

# Target subreddits
TARGET_SUBREDDITS = os.environ.get(
    'TARGET_SUBREDDITS',
    'wallstreetbets,stocks,investing,stockmarket,options'
).split(',')

# Worker settings
POSTS_PER_SUBREDDIT = int(os.environ.get('POSTS_PER_SUBREDDIT', '100'))
DAEMON_SLEEP_SECONDS = int(os.environ.get('DAEMON_SLEEP_SECONDS', '600'))  # 10 minutes
SUBREDDIT_DELAY_SECONDS = int(os.environ.get('SUBREDDIT_DELAY_SECONDS', '5'))  # Between subreddits
POST_DELAY_SECONDS = float(os.environ.get('POST_DELAY_SECONDS', '0.5'))  # Between posts

# ============================================================================
# Logging setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# AWS Clients
# ============================================================================

boto_config = Config(
    region_name=AWS_REGION,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

dynamodb = boto3.resource('dynamodb', config=boto_config)
ssm = boto3.client('ssm', config=boto_config)

stocks_table = dynamodb.Table(STOCKS_TABLE)
mentions_table = dynamodb.Table(MENTIONS_TABLE)
metadata_table = dynamodb.Table(METADATA_TABLE)

# ============================================================================
# Ticker extraction
# ============================================================================

# Valid tickers cache
VALID_TICKERS: Optional[Set[str]] = None


def load_valid_tickers() -> Set[str]:
    """Load all valid tickers from DynamoDB stocks table."""
    global VALID_TICKERS

    if VALID_TICKERS is not None:
        return VALID_TICKERS

    VALID_TICKERS = set()

    try:
        logger.info("Loading valid tickers from DynamoDB...")
        response = stocks_table.scan(ProjectionExpression='ticker')

        for item in response.get('Items', []):
            VALID_TICKERS.add(item['ticker'])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = stocks_table.scan(
                ProjectionExpression='ticker',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            for item in response.get('Items', []):
                VALID_TICKERS.add(item['ticker'])

        logger.info(f"Loaded {len(VALID_TICKERS)} valid tickers")

    except Exception as e:
        logger.error(f"Error loading tickers: {e}")

    return VALID_TICKERS


def extract_tickers(text: str, valid_tickers: Set[str]) -> List[str]:
    """
    Extract stock tickers from text.
    Matches:
    - $AAPL format (most reliable)
    - AAPL (uppercase, 2-5 chars, word boundary)

    Special handling:
    - "AI" only matched if prefixed with $ or as "C3.ai"
    - Excludes contractions like "don't" → DON
    """
    found_tickers = set()

    # Pattern for $TICKER format
    # Negative lookbehind to avoid matching apostrophes (e.g., "don't" → "DON")
    dollar_pattern = r'(?<![a-zA-Z\'])\$([A-Z]{1,5})\b'
    for match in re.finditer(dollar_pattern, text.upper()):
        ticker = match.group(1)
        if ticker in valid_tickers:
            found_tickers.add(ticker)

    # Special case: Match "C3.ai" or "C3 AI" for AI ticker
    c3ai_pattern = r'\bC3[\.\s]?AI\b'
    if re.search(c3ai_pattern, text, re.IGNORECASE) and 'AI' in valid_tickers:
        found_tickers.add('AI')

    # Pattern for plain TICKER format (must be uppercase in original)
    # Excludes apostrophes and special handling for "AI"
    plain_pattern = r'(?<![a-zA-Z\'])\b([A-Z]{2,5})\b(?![a-zA-Z\'])'
    for match in re.finditer(plain_pattern, text):
        ticker = match.group(1)

        # Skip "AI" in plain format (only match with $ or C3.ai)
        if ticker == 'AI':
            continue

        if ticker in valid_tickers:
            found_tickers.add(ticker)

    return list(found_tickers)

# ============================================================================
# Reddit client
# ============================================================================


def get_reddit_credentials() -> Dict[str, str]:
    """Get Reddit credentials from environment or SSM."""
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        logger.info("Using Reddit credentials from environment")
        return {
            'client_id': REDDIT_CLIENT_ID,
            'client_secret': REDDIT_CLIENT_SECRET
        }

    logger.info("Fetching Reddit credentials from SSM Parameter Store...")
    response = ssm.get_parameters(
        Names=[SSM_CLIENT_ID_PARAM, SSM_CLIENT_SECRET_PARAM],
        WithDecryption=True
    )

    params = {p['Name']: p['Value'] for p in response['Parameters']}

    if SSM_CLIENT_ID_PARAM not in params or SSM_CLIENT_SECRET_PARAM not in params:
        raise ValueError("Reddit credentials not found in SSM Parameter Store")

    return {
        'client_id': params[SSM_CLIENT_ID_PARAM],
        'client_secret': params[SSM_CLIENT_SECRET_PARAM]
    }


def create_reddit_client() -> praw.Reddit:
    """Create and return a PRAW Reddit client."""
    creds = get_reddit_credentials()

    reddit = praw.Reddit(
        client_id=creds['client_id'],
        client_secret=creds['client_secret'],
        user_agent='stock-mentions:v2.0 (by /u/stock-mentions-bot)'
    )
    reddit.read_only = True

    logger.info("Reddit client initialized (read-only mode)")
    return reddit

# ============================================================================
# Metadata tracking
# ============================================================================


def get_last_fetch_time(subreddit: str) -> float:
    """Get the last fetch timestamp for a subreddit."""
    try:
        response = metadata_table.get_item(
            Key={'key': f'last_fetch_{subreddit}'}
        )
        if 'Item' in response:
            return float(response['Item']['timestamp'])
    except Exception as e:
        logger.warning(f"Error getting last fetch time for {subreddit}: {e}")

    # Default to 1 hour ago
    return datetime.now(timezone.utc).timestamp() - 3600


def set_last_fetch_time(subreddit: str, timestamp: float):
    """Update the last fetch timestamp for a subreddit."""
    try:
        metadata_table.put_item(Item={
            'key': f'last_fetch_{subreddit}',
            'timestamp': str(timestamp),
            'updated_at': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error setting last fetch time for {subreddit}: {e}")

# ============================================================================
# DynamoDB storage
# ============================================================================


def store_mentions_batch(mentions: List[Dict[str, Any]]) -> int:
    """
    Store mentions in DynamoDB using batch write.
    Returns number of successfully written items.
    """
    if not mentions:
        return 0

    written = 0

    # DynamoDB batch_write_item limit is 25 items
    for i in range(0, len(mentions), 25):
        batch = mentions[i:i + 25]

        try:
            with mentions_table.batch_writer() as writer:
                for item in batch:
                    writer.put_item(Item=item)
                written += len(batch)
        except Exception as e:
            logger.error(f"Error in batch write: {e}")

    return written


def create_mention_item(ticker: str, data: Dict[str, Any], is_comment: bool) -> Dict[str, Any]:
    """Create a DynamoDB item for a ticker mention."""
    timestamp = datetime.fromtimestamp(
        data['created_utc'],
        tz=timezone.utc
    ).isoformat()

    item_id = data.get('comment_id') if is_comment else data['post_id']
    sort_key = f"{timestamp}#{item_id}"

    item = {
        'ticker': ticker,
        'timestamp_post_id': sort_key,
        'subreddit': data['subreddit'],
        'post_id': data['post_id'],
        'author': data['author'],
        'upvotes': data['upvotes'],
        'url': data['url'],
        'created_utc': int(data['created_utc']),
        'source_type': 'comment' if is_comment else 'post'
    }

    if is_comment:
        item['comment_id'] = data['comment_id']
        item['comment_body'] = data.get('body', '')[:5000]  # Truncate long comments
        item['parent_id'] = data.get('parent_id', '')
    else:
        item['post_title'] = data.get('title', '')
        item['post_body'] = data.get('selftext', '')[:10000]  # Truncate long posts

    return item

# ============================================================================
# Main worker logic
# ============================================================================


def process_subreddit(
    reddit: praw.Reddit,
    subreddit_name: str,
    valid_tickers: Set[str],
    posts_limit: int = 100
) -> Dict[str, int]:
    """
    Process a single subreddit: fetch posts, comments, extract tickers, store mentions.
    Returns stats dict.
    """
    stats = {
        'posts_fetched': 0,
        'comments_fetched': 0,
        'mentions_stored': 0
    }

    last_fetch = get_last_fetch_time(subreddit_name)
    latest_timestamp = last_fetch
    mentions_to_store = []

    logger.info(f"Processing r/{subreddit_name} (posts since {datetime.fromtimestamp(last_fetch)})")

    try:
        subreddit = reddit.subreddit(subreddit_name)

        for submission in subreddit.new(limit=posts_limit):
            # Skip posts older than last fetch
            if submission.created_utc <= last_fetch:
                continue

            stats['posts_fetched'] += 1

            # Track latest timestamp
            if submission.created_utc > latest_timestamp:
                latest_timestamp = submission.created_utc

            # Process post
            post_data = {
                'post_id': submission.id,
                'subreddit': subreddit_name,
                'title': submission.title,
                'selftext': submission.selftext or '',
                'author': str(submission.author) if submission.author else '[deleted]',
                'upvotes': submission.score,
                'url': f'https://reddit.com{submission.permalink}',
                'created_utc': submission.created_utc
            }

            # Extract tickers from post
            post_text = f"{submission.title} {submission.selftext or ''}"
            post_tickers = extract_tickers(post_text, valid_tickers)

            for ticker in post_tickers:
                mentions_to_store.append(
                    create_mention_item(ticker, post_data, is_comment=False)
                )

            # Fetch ALL comments
            try:
                logger.debug(f"  Fetching comments for post {submission.id}...")

                # replace_more(limit=None) fetches ALL "load more" comment stubs
                # This can take time on hot posts but ensures we get everything
                submission.comments.replace_more(limit=None)

                for comment in submission.comments.list():
                    # Skip old comments
                    if comment.created_utc <= last_fetch:
                        continue

                    stats['comments_fetched'] += 1

                    comment_data = {
                        'post_id': submission.id,
                        'comment_id': comment.id,
                        'subreddit': subreddit_name,
                        'parent_id': str(comment.parent_id),
                        'body': comment.body,
                        'author': str(comment.author) if comment.author else '[deleted]',
                        'upvotes': comment.score,
                        'url': f'https://reddit.com{comment.permalink}',
                        'created_utc': comment.created_utc
                    }

                    # Extract tickers from comment
                    comment_tickers = extract_tickers(comment.body, valid_tickers)

                    for ticker in comment_tickers:
                        mentions_to_store.append(
                            create_mention_item(ticker, comment_data, is_comment=True)
                        )

            except Exception as e:
                logger.warning(f"  Error fetching comments for {submission.id}: {e}")

            # Small delay between posts to respect rate limits
            time.sleep(POST_DELAY_SECONDS)

        # Store all mentions
        if mentions_to_store:
            stats['mentions_stored'] = store_mentions_batch(mentions_to_store)

        # Update last fetch time
        if latest_timestamp > last_fetch:
            set_last_fetch_time(subreddit_name, latest_timestamp)

    except Exception as e:
        logger.error(f"Error processing r/{subreddit_name}: {e}")

    logger.info(
        f"r/{subreddit_name}: {stats['posts_fetched']} posts, "
        f"{stats['comments_fetched']} comments, "
        f"{stats['mentions_stored']} mentions stored"
    )

    return stats


def run_worker(posts_limit: int = 100) -> Dict[str, Any]:
    """
    Run a single worker cycle across all subreddits.
    Returns aggregate stats.
    """
    start_time = time.time()

    # Load valid tickers
    valid_tickers = load_valid_tickers()
    if not valid_tickers:
        logger.error("No valid tickers loaded. Run stock_sync.py first!")
        return {'error': 'No tickers loaded'}

    # Create Reddit client
    reddit = create_reddit_client()

    # Aggregate stats
    total_stats = {
        'posts_fetched': 0,
        'comments_fetched': 0,
        'mentions_stored': 0,
        'subreddits_processed': 0
    }

    for subreddit_name in TARGET_SUBREDDITS:
        stats = process_subreddit(reddit, subreddit_name, valid_tickers, posts_limit)

        total_stats['posts_fetched'] += stats['posts_fetched']
        total_stats['comments_fetched'] += stats['comments_fetched']
        total_stats['mentions_stored'] += stats['mentions_stored']
        total_stats['subreddits_processed'] += 1

        # Delay between subreddits
        if subreddit_name != TARGET_SUBREDDITS[-1]:
            logger.info(f"Waiting {SUBREDDIT_DELAY_SECONDS}s before next subreddit...")
            time.sleep(SUBREDDIT_DELAY_SECONDS)

    elapsed = time.time() - start_time
    total_stats['elapsed_seconds'] = round(elapsed, 2)

    logger.info(
        f"Worker cycle complete: {total_stats['posts_fetched']} posts, "
        f"{total_stats['comments_fetched']} comments, "
        f"{total_stats['mentions_stored']} mentions in {elapsed:.1f}s"
    )

    return total_stats


def run_daemon():
    """Run worker in daemon mode (continuous loop)."""
    logger.info(f"Starting daemon mode (sleep interval: {DAEMON_SLEEP_SECONDS}s)")

    cycle = 0
    while True:
        cycle += 1
        logger.info(f"=== Daemon cycle {cycle} ===")

        try:
            run_worker()
        except Exception as e:
            logger.error(f"Error in worker cycle: {e}")

        logger.info(f"Sleeping for {DAEMON_SLEEP_SECONDS}s...")
        time.sleep(DAEMON_SLEEP_SECONDS)

# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description='Stock Mentions EC2 Worker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python worker.py              # Single run
  python worker.py --daemon     # Continuous mode
  python worker.py --backfill   # Fetch more historical posts
        """
    )
    parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run in daemon mode (continuous loop)'
    )
    parser.add_argument(
        '--backfill', '-b',
        action='store_true',
        help='Backfill mode: fetch more posts (500 instead of 100)'
    )
    parser.add_argument(
        '--subreddit', '-s',
        type=str,
        help='Process only this subreddit'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Override subreddits if specified
    global TARGET_SUBREDDITS
    if args.subreddit:
        TARGET_SUBREDDITS = [args.subreddit]
        logger.info(f"Processing single subreddit: {args.subreddit}")

    posts_limit = 500 if args.backfill else POSTS_PER_SUBREDDIT

    if args.daemon:
        run_daemon()
    else:
        stats = run_worker(posts_limit)
        print(f"\nStats: {stats}")


if __name__ == '__main__':
    main()
