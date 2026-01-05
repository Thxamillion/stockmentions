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
    Returns top mentioned tickers with comment/thread breakdown.
    Also supports breakdown by subreddit via query parameter.
    """
    params = event.get('queryStringParameters') or {}
    period = params.get('period', '24h')
    by_subreddit = params.get('by_subreddit', 'false').lower() == 'true'
    
    period_start = get_period_start(period)

    # Scan mentions table for recent mentions
    # Note: For production, consider using a pre-aggregated table
    ticker_data = {}  # ticker -> {comments: int, threads: int}
    subreddit_data = {}  # subreddit -> {ticker -> {comments, threads}}

    try:
        response = mentions_table.scan(
            FilterExpression='timestamp_post_id >= :start',
            ExpressionAttributeValues={':start': period_start}
        )

        for item in response.get('Items', []):
            ticker = item['ticker']
            source_type = item.get('source_type', 'post')
            subreddit = item.get('subreddit', 'unknown')
            
            # Overall ticker data
            if ticker not in ticker_data:
                ticker_data[ticker] = {'comments': 0, 'threads': 0}
            
            if source_type == 'comment':
                ticker_data[ticker]['comments'] += 1
            else:
                ticker_data[ticker]['threads'] += 1
            
            # Per-subreddit ticker data
            if by_subreddit:
                if subreddit not in subreddit_data:
                    subreddit_data[subreddit] = {}
                if ticker not in subreddit_data[subreddit]:
                    subreddit_data[subreddit][ticker] = {'comments': 0, 'threads': 0}
                
                if source_type == 'comment':
                    subreddit_data[subreddit][ticker]['comments'] += 1
                else:
                    subreddit_data[subreddit][ticker]['threads'] += 1

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = mentions_table.scan(
                FilterExpression='timestamp_post_id >= :start',
                ExpressionAttributeValues={':start': period_start},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            for item in response.get('Items', []):
                ticker = item['ticker']
                source_type = item.get('source_type', 'post')
                subreddit = item.get('subreddit', 'unknown')
                
                if ticker not in ticker_data:
                    ticker_data[ticker] = {'comments': 0, 'threads': 0}
                
                if source_type == 'comment':
                    ticker_data[ticker]['comments'] += 1
                else:
                    ticker_data[ticker]['threads'] += 1
                
                if by_subreddit:
                    if subreddit not in subreddit_data:
                        subreddit_data[subreddit] = {}
                    if ticker not in subreddit_data[subreddit]:
                        subreddit_data[subreddit][ticker] = {'comments': 0, 'threads': 0}
                    
                    if source_type == 'comment':
                        subreddit_data[subreddit][ticker]['comments'] += 1
                    else:
                        subreddit_data[subreddit][ticker]['threads'] += 1

    except Exception as e:
        print(f"Error scanning mentions: {e}")
        return json_response(500, {'error': 'Failed to fetch trending data'})

    # Build response
    response_data = {
        'period': period,
        'lastUpdated': datetime.now(timezone.utc).isoformat()
    }
    
    if by_subreddit:
        # Format by subreddit
        subreddits = []
        for subreddit_name, tickers in subreddit_data.items():
            sorted_tickers = sorted(
                tickers.items(),
                key=lambda x: x[1]['comments'] + x[1]['threads'],
                reverse=True
            )[:10]
            
            rows = [
                {
                    'ticker': ticker,
                    'comments': data['comments'],
                    'threads': data['threads']
                }
                for ticker, data in sorted_tickers
            ]
            
            subreddits.append({
                'id': subreddit_name,
                'name': f'r/{subreddit_name}',
                'rows': rows
            })
        
        # Overall top tickers
        sorted_all = sorted(
            ticker_data.items(),
            key=lambda x: x[1]['comments'] + x[1]['threads'],
            reverse=True
        )[:10]
        
        all_tickers = [
            {
                'ticker': ticker,
                'comments': data['comments'],
                'threads': data['threads']
            }
            for ticker, data in sorted_all
        ]
        
        response_data['subreddits'] = subreddits
        response_data['all'] = all_tickers
    else:
        # Simple format - just top tickers
        sorted_tickers = sorted(
            ticker_data.items(),
            key=lambda x: x[1]['comments'] + x[1]['threads'],
            reverse=True
        )[:20]

        data = [
            {
                'ticker': ticker,
                'comments': data['comments'],
                'threads': data['threads']
            }
            for ticker, data in sorted_tickers
        ]
        response_data['data'] = data

    return json_response(200, response_data)


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

    # Count by source type
    post_count = sum(1 for m in mentions if m.get('source_type') == 'post')
    comment_count = sum(1 for m in mentions if m.get('source_type') == 'comment')

    # Format recent posts (top 10)
    recent_posts = []
    for m in mentions[:10]:
        item = {
            'subreddit': m['subreddit'],
            'upvotes': m['upvotes'],
            'url': m['url'],
            'timestamp': m['timestamp_post_id'].split('#')[0],
            'source_type': m.get('source_type', 'post')
        }
        
        if m.get('source_type') == 'comment':
            item['comment_body'] = m.get('comment_body', '')[:200]  # Truncate
        else:
            item['title'] = m.get('post_title', '')
        
        recent_posts.append(item)

    return json_response(200, {
        'ticker': symbol,
        'company_name': stock_info.get('company_name', ''),
        'period': period,
        'total_mentions': len(mentions),
        'post_mentions': post_count,
        'comment_mentions': comment_count,
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

    ticker_data = {}  # ticker -> {comments: int, threads: int}

    try:
        # Query the GSI by subreddit
        response = mentions_table.query(
            IndexName='by-subreddit',
            KeyConditionExpression=Key('subreddit').eq(name) & Key('timestamp_post_id').gte(period_start),
            ScanIndexForward=False
        )

        for item in response.get('Items', []):
            ticker = item['ticker']
            source_type = item.get('source_type', 'post')
            
            if ticker not in ticker_data:
                ticker_data[ticker] = {'comments': 0, 'threads': 0}
            
            if source_type == 'comment':
                ticker_data[ticker]['comments'] += 1
            else:
                ticker_data[ticker]['threads'] += 1

    except Exception as e:
        print(f"Error querying subreddit: {e}")
        return json_response(500, {'error': 'Failed to fetch subreddit data'})

    # Sort by total mentions (comments + threads)
    sorted_tickers = sorted(
        ticker_data.items(),
        key=lambda x: x[1]['comments'] + x[1]['threads'],
        reverse=True
    )[:20]

    top_tickers = [
        {
            'ticker': ticker,
            'comments': data['comments'],
            'threads': data['threads']
        }
        for ticker, data in sorted_tickers
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
