"""
Trends Aggregator Lambda
Runs hourly to pre-compute trending tickers from mentions data.
Writes aggregated results to trends table for fast API queries.
"""

import os
import json
import boto3
from datetime import datetime, timezone, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
mentions_table = dynamodb.Table(os.environ['MENTIONS_TABLE'])
trends_table = dynamodb.Table(os.environ['TRENDS_TABLE'])

PERIODS = ['24h', '7d', '30d']


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


def aggregate_mentions(period):
    """
    Scan mentions table and aggregate by ticker for the given period.
    Returns: {ticker: {comments: int, threads: int}}
    """
    period_start = get_period_start(period)
    ticker_data = {}

    print(f"Aggregating {period} mentions (since {period_start})...")

    try:
        # Scan mentions table with time filter
        response = mentions_table.scan(
            FilterExpression='timestamp_post_id >= :start',
            ExpressionAttributeValues={':start': period_start}
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

                if ticker not in ticker_data:
                    ticker_data[ticker] = {'comments': 0, 'threads': 0}

                if source_type == 'comment':
                    ticker_data[ticker]['comments'] += 1
                else:
                    ticker_data[ticker]['threads'] += 1

        print(f"  Found {len(ticker_data)} unique tickers")
        return ticker_data

    except Exception as e:
        print(f"Error aggregating mentions for {period}: {e}")
        raise


def write_trends(period, ticker_data):
    """
    Write aggregated trend data to trends table.
    Uses batch writes for efficiency.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Prepare items for batch write
    items = []
    for ticker, data in ticker_data.items():
        mention_count = data['comments'] + data['threads']

        items.append({
            'period': period,
            'ticker': ticker,
            'mention_count': Decimal(str(mention_count)),
            'comment_count': Decimal(str(data['comments'])),
            'thread_count': Decimal(str(data['threads'])),
            'last_updated': now
        })

    # Write in batches of 25 (DynamoDB limit)
    print(f"Writing {len(items)} trend items to DynamoDB...")

    for i in range(0, len(items), 25):
        batch = items[i:i+25]

        with trends_table.batch_writer() as writer:
            for item in batch:
                writer.put_item(Item=item)

    print(f"  ✓ Wrote {len(items)} items for period {period}")


def lambda_handler(event, context):
    """
    Main handler - aggregates mentions for all time periods.
    Triggered hourly by EventBridge.
    """
    print("=== Trends Aggregation Starting ===")
    start_time = datetime.now(timezone.utc)

    results = {
        'timestamp': start_time.isoformat(),
        'periods': {}
    }

    for period in PERIODS:
        try:
            # Aggregate mentions for this period
            ticker_data = aggregate_mentions(period)

            # Write to trends table
            write_trends(period, ticker_data)

            results['periods'][period] = {
                'unique_tickers': len(ticker_data),
                'total_mentions': sum(d['comments'] + d['threads'] for d in ticker_data.values()),
                'status': 'success'
            }

        except Exception as e:
            print(f"ERROR processing {period}: {e}")
            results['periods'][period] = {
                'status': 'error',
                'error': str(e)
            }

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    results['duration_seconds'] = duration

    print(f"=== Aggregation Complete in {duration:.1f}s ===")
    print(json.dumps(results, indent=2))

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
