"""
API Handler Lambda
Handles all API Gateway requests for the Stock Mentions API.
"""

import os
import json
import boto3
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
stocks_table = dynamodb.Table(os.environ['STOCKS_TABLE'])
mentions_table = dynamodb.Table(os.environ['MENTIONS_TABLE'])


def get_period_start(period):
    """Get the start timestamp for a given period."""
    now = datetime.now(timezone.utc)

    if period == '7d':
        delta = timedelta(days=7)
    elif period == '30d':
        delta = timedelta(days=30)
    else:  # Default 24h
        delta = timedelta(hours=24)

    return (now - delta).isoformat()


def json_response(status_code, body):
    """Create a JSON API response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }


def handle_trending(event):
    """
    GET /trending
    Returns top mentioned tickers in the last 24 hours.
    """
    period_start = get_period_start('24h')

    # Scan mentions table for recent mentions
    # Note: For production, consider using a pre-aggregated table
    ticker_counts = {}

    try:
        response = mentions_table.scan(
            FilterExpression='timestamp_post_id >= :start',
            ExpressionAttributeValues={':start': period_start}
        )

        for item in response.get('Items', []):
            ticker = item['ticker']
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = mentions_table.scan(
                FilterExpression='timestamp_post_id >= :start',
                ExpressionAttributeValues={':start': period_start},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            for item in response.get('Items', []):
                ticker = item['ticker']
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

    except Exception as e:
        print(f"Error scanning mentions: {e}")
        return json_response(500, {'error': 'Failed to fetch trending data'})

    # Sort by count and take top 20
    sorted_tickers = sorted(
        ticker_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:20]

    data = [
        {'ticker': ticker, 'mentions': count, 'change': None}
        for ticker, count in sorted_tickers
    ]

    return json_response(200, {
        'period': '24h',
        'data': data
    })


def handle_ticker(event, symbol):
    """
    GET /ticker/{symbol}
    Returns mention history for a specific ticker.
    """
    symbol = symbol.upper()
    period = event.get('queryStringParameters', {}).get('period', '24h') if event.get('queryStringParameters') else '24h'
    period_start = get_period_start(period)

    # Get stock info
    stock_info = None
    try:
        response = stocks_table.get_item(Key={'ticker': symbol})
        stock_info = response.get('Item')
    except Exception as e:
        print(f"Error fetching stock info: {e}")

    if not stock_info:
        return json_response(404, {'error': f'Ticker {symbol} not found'})

    # Get mentions for this ticker
    mentions = []
    by_subreddit = {}

    try:
        response = mentions_table.query(
            KeyConditionExpression=Key('ticker').eq(symbol) & Key('timestamp_post_id').gte(period_start),
            ScanIndexForward=False  # Most recent first
        )

        for item in response.get('Items', []):
            mentions.append(item)
            sub = item['subreddit']
            by_subreddit[sub] = by_subreddit.get(sub, 0) + 1

    except Exception as e:
        print(f"Error querying mentions: {e}")
        return json_response(500, {'error': 'Failed to fetch ticker data'})

    # Format recent posts (top 10)
    recent_posts = [
        {
            'subreddit': m['subreddit'],
            'title': m['post_title'],
            'upvotes': m['upvotes'],
            'url': m['url'],
            'timestamp': m['timestamp_post_id'].split('#')[0]
        }
        for m in mentions[:10]
    ]

    return json_response(200, {
        'ticker': symbol,
        'company_name': stock_info.get('company_name', ''),
        'period': period,
        'total_mentions': len(mentions),
        'by_subreddit': by_subreddit,
        'recent_posts': recent_posts
    })


def handle_subreddit(event, name):
    """
    GET /subreddit/{name}
    Returns top tickers for a specific subreddit.
    """
    period = event.get('queryStringParameters', {}).get('period', '24h') if event.get('queryStringParameters') else '24h'
    period_start = get_period_start(period)

    ticker_counts = {}

    try:
        # Query the GSI by subreddit
        response = mentions_table.query(
            IndexName='by-subreddit',
            KeyConditionExpression=Key('subreddit').eq(name) & Key('timestamp_post_id').gte(period_start),
            ScanIndexForward=False
        )

        for item in response.get('Items', []):
            ticker = item['ticker']
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

    except Exception as e:
        print(f"Error querying subreddit: {e}")
        return json_response(500, {'error': 'Failed to fetch subreddit data'})

    # Sort by count
    sorted_tickers = sorted(
        ticker_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:20]

    top_tickers = [
        {'ticker': ticker, 'mentions': count}
        for ticker, count in sorted_tickers
    ]

    return json_response(200, {
        'subreddit': name,
        'period': period,
        'top_tickers': top_tickers
    })


def lambda_handler(event, context):
    """Main Lambda handler - routes API requests."""
    print(f"Received event: {json.dumps(event)}")

    # Extract route info from API Gateway v2 format
    route_key = event.get('routeKey', '')
    path_params = event.get('pathParameters', {}) or {}

    # Route to appropriate handler
    if route_key == 'GET /trending':
        return handle_trending(event)

    elif route_key == 'GET /ticker/{symbol}':
        symbol = path_params.get('symbol', '')
        return handle_ticker(event, symbol)

    elif route_key == 'GET /subreddit/{name}':
        name = path_params.get('name', '')
        return handle_subreddit(event, name)

    else:
        return json_response(404, {'error': 'Not found'})
