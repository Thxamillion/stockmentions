"""
Mention Processor Lambda
Processes Reddit posts from SQS, extracts ticker mentions, and stores in DynamoDB.
"""

import os
import re
import json
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
stocks_table = dynamodb.Table(os.environ['STOCKS_TABLE'])
mentions_table = dynamodb.Table(os.environ['MENTIONS_TABLE'])

# Cache for valid tickers (loaded once per Lambda instance)
VALID_TICKERS = None


def load_valid_tickers():
    """Load all valid tickers from DynamoDB."""
    global VALID_TICKERS

    if VALID_TICKERS is not None:
        return VALID_TICKERS

    VALID_TICKERS = set()

    try:
        # Scan all tickers (this table is small enough)
        response = stocks_table.scan(
            ProjectionExpression='ticker'
        )

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

        print(f"Loaded {len(VALID_TICKERS)} valid tickers")

    except Exception as e:
        print(f"Error loading tickers: {e}")

    return VALID_TICKERS


def extract_tickers(text, valid_tickers):
    """
    Extract stock tickers from text.
    Matches:
    - $AAPL format
    - AAPL (uppercase, 1-5 chars, word boundary)
    """
    found_tickers = set()

    # Pattern for $TICKER format (most reliable)
    dollar_pattern = r'\$([A-Z]{1,5})\b'
    for match in re.finditer(dollar_pattern, text.upper()):
        ticker = match.group(1)
        if ticker in valid_tickers:
            found_tickers.add(ticker)

    # Pattern for plain TICKER format (uppercase words)
    # More strict - must be uppercase in original text
    plain_pattern = r'\b([A-Z]{2,5})\b'
    for match in re.finditer(plain_pattern, text):
        ticker = match.group(1)
        if ticker in valid_tickers:
            found_tickers.add(ticker)

    return list(found_tickers)


def store_mention(ticker, post_data):
    """Store a ticker mention in DynamoDB."""
    timestamp = datetime.fromtimestamp(
        post_data['created_utc'],
        tz=timezone.utc
    ).isoformat()

    # Sort key format: timestamp#post_id
    sort_key = f"{timestamp}#{post_data['post_id']}"

    try:
        mentions_table.put_item(Item={
            'ticker': ticker,
            'timestamp_post_id': sort_key,
            'subreddit': post_data['subreddit'],
            'post_id': post_data['post_id'],
            'post_title': post_data['title'],
            'author': post_data['author'],
            'upvotes': post_data['upvotes'],
            'url': post_data['url'],
            'created_utc': int(post_data['created_utc'])
        })
        return True
    except Exception as e:
        print(f"Error storing mention for {ticker}: {e}")
        return False


def lambda_handler(event, context):
    """Main Lambda handler - triggered by SQS."""
    print(f"Processing {len(event['Records'])} SQS messages")

    # Load valid tickers
    valid_tickers = load_valid_tickers()

    if not valid_tickers:
        print("Warning: No valid tickers loaded, skipping processing")
        return {'statusCode': 200, 'body': 'No tickers loaded'}

    total_mentions = 0
    processed_posts = 0

    for record in event['Records']:
        try:
            post_data = json.loads(record['body'])
            processed_posts += 1

            # Extract tickers from title
            tickers = extract_tickers(post_data['title'], valid_tickers)

            if tickers:
                print(f"Found tickers {tickers} in: {post_data['title'][:50]}...")

                for ticker in tickers:
                    if store_mention(ticker, post_data):
                        total_mentions += 1

        except Exception as e:
            print(f"Error processing record: {e}")

    print(f"Processed {processed_posts} posts, stored {total_mentions} mentions")

    return {
        'statusCode': 200,
        'body': {
            'posts_processed': processed_posts,
            'mentions_stored': total_mentions
        }
    }
