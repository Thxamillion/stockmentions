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

    # Determine source type
    is_comment = post_data.get('is_comment', False)
    
    # Sort key format: timestamp#post_id or timestamp#comment_id
    item_id = post_data.get('comment_id') if is_comment else post_data['post_id']
    sort_key = f"{timestamp}#{item_id}"

    try:
        item = {
            'ticker': ticker,
            'timestamp_post_id': sort_key,
            'subreddit': post_data['subreddit'],
            'post_id': post_data['post_id'],
            'author': post_data['author'],
            'upvotes': post_data['upvotes'],
            'url': post_data['url'],
            'created_utc': int(post_data['created_utc']),
            'source_type': 'comment' if is_comment else 'post'
        }
        
        # Add type-specific fields
        if is_comment:
            item['comment_id'] = post_data['comment_id']
            item['comment_body'] = post_data.get('body', '')
            item['parent_id'] = post_data.get('parent_id', '')
        else:
            item['post_title'] = post_data.get('title', '')
            item['post_body'] = post_data.get('selftext', '')
        
        mentions_table.put_item(Item=item)
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

            # Determine what text to scan
            is_comment = post_data.get('is_comment', False)
            
            if is_comment:
                # For comments, scan the comment body
                text_to_scan = post_data.get('body', '')
                preview = text_to_scan[:50]
            else:
                # For posts, scan title + selftext
                title = post_data.get('title', '')
                selftext = post_data.get('selftext', '')
                text_to_scan = f"{title} {selftext}"
                preview = post_data.get('title', '')[:50]

            # Extract tickers
            tickers = extract_tickers(text_to_scan, valid_tickers)

            if tickers:
                source = "comment" if is_comment else "post"
                print(f"Found tickers {tickers} in {source}: {preview}...")

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
