"""
Stock Sync Lambda
Fetches NASDAQ and NYSE stock lists and stores them in DynamoDB.
"""

import os
import urllib.request
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
stocks_table = dynamodb.Table(os.environ['STOCKS_TABLE'])

# Common words that are also tickers - skip these to avoid false positives
SKIP_TICKERS = {
    'A', 'I', 'AM', 'AN', 'AS', 'AT', 'BE', 'BY', 'DO', 'GO', 'HE', 'IF', 'IN',
    'IS', 'IT', 'ME', 'MY', 'NO', 'OF', 'OK', 'ON', 'OR', 'SO', 'TO', 'UP', 'US',
    'WE', 'ALL', 'AND', 'ANY', 'ARE', 'BIG', 'BUT', 'CAN', 'DAY', 'DID', 'FOR',
    'GET', 'GOT', 'HAD', 'HAS', 'HER', 'HIM', 'HIS', 'HOW', 'ITS', 'LET', 'MAY',
    'NEW', 'NOT', 'NOW', 'OLD', 'ONE', 'OUR', 'OUT', 'OWN', 'SAY', 'SHE', 'THE',
    'TOO', 'TWO', 'WAY', 'WHO', 'WHY', 'YES', 'YET', 'YOU', 'BEST', 'CASH', 'EDIT',
    'EVER', 'EYES', 'FIND', 'FREE', 'GOOD', 'HEAR', 'HELP', 'HERE', 'HOLD', 'HOME',
    'HOPE', 'INFO', 'JUST', 'KNOW', 'LIFE', 'LIKE', 'LIST', 'LIVE', 'LONG', 'LOOK',
    'LOVE', 'MADE', 'MAIN', 'MAKE', 'MIND', 'MORE', 'MOST', 'MUCH', 'MUST', 'NEED',
    'NEXT', 'NICE', 'OPEN', 'OVER', 'PLAY', 'POST', 'PUMP', 'PURE', 'REAL', 'RIDE',
    'RISK', 'SAFE', 'SAME', 'SAVE', 'SELF', 'SELL', 'SHOP', 'SHOW', 'STAY', 'STOP',
    'SURE', 'TAKE', 'TALK', 'TELL', 'THAN', 'THAT', 'THEM', 'THEN', 'THEY', 'THIS',
    'TIME', 'TURN', 'VERY', 'WANT', 'WELL', 'WERE', 'WHAT', 'WHEN', 'WILL', 'WITH',
    'WORK', 'YOLO', 'YOUR', 'ZERO', 'DD', 'CEO', 'CFO', 'IPO', 'ETF', 'GDP', 'USA',
    'LLC', 'INC', 'EPS', 'ATH', 'FUD', 'IMO', 'LOL', 'OMG', 'SEC', 'WSB', 'RH',
    'TD', 'TA', 'FA', 'PT', 'PM', 'ER'
}

NASDAQ_URL = 'ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt'
OTHER_URL = 'ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt'


def fetch_nasdaq_stocks():
    """Fetch NASDAQ-listed stocks."""
    stocks = []
    try:
        with urllib.request.urlopen(NASDAQ_URL, timeout=30) as response:
            content = response.read().decode('utf-8')
            lines = content.strip().split('\n')

            # Skip header and footer
            for line in lines[1:]:
                if line.startswith('File Creation Time'):
                    break

                parts = line.split('|')
                if len(parts) >= 2:
                    ticker = parts[0].strip()
                    company_name = parts[1].strip()

                    # Skip test stocks and invalid tickers
                    if ticker and not ticker.endswith('Y') and ticker not in SKIP_TICKERS:
                        stocks.append({
                            'ticker': ticker,
                            'company_name': company_name,
                            'exchange': 'NASDAQ'
                        })
    except Exception as e:
        print(f"Error fetching NASDAQ stocks: {e}")

    return stocks


def fetch_other_stocks():
    """Fetch NYSE and other exchange stocks."""
    stocks = []
    try:
        with urllib.request.urlopen(OTHER_URL, timeout=30) as response:
            content = response.read().decode('utf-8')
            lines = content.strip().split('\n')

            # Skip header and footer
            for line in lines[1:]:
                if line.startswith('File Creation Time'):
                    break

                parts = line.split('|')
                if len(parts) >= 3:
                    ticker = parts[0].strip()
                    company_name = parts[1].strip()
                    exchange = parts[2].strip()

                    # Map exchange codes
                    exchange_map = {
                        'A': 'NYSE American',
                        'N': 'NYSE',
                        'P': 'NYSE Arca',
                        'Z': 'BATS',
                        'V': 'IEX'
                    }
                    exchange_name = exchange_map.get(exchange, exchange)

                    if ticker and ticker not in SKIP_TICKERS:
                        stocks.append({
                            'ticker': ticker,
                            'company_name': company_name,
                            'exchange': exchange_name
                        })
    except Exception as e:
        print(f"Error fetching other stocks: {e}")

    return stocks


def batch_write_stocks(stocks):
    """Write stocks to DynamoDB in batches."""
    timestamp = datetime.now(timezone.utc).isoformat()

    with stocks_table.batch_writer() as batch:
        for stock in stocks:
            batch.put_item(Item={
                'ticker': stock['ticker'],
                'company_name': stock['company_name'],
                'exchange': stock['exchange'],
                'updated_at': timestamp
            })


def lambda_handler(event, context):
    """Main Lambda handler."""
    print("Starting stock sync...")

    # Fetch from both sources
    nasdaq_stocks = fetch_nasdaq_stocks()
    print(f"Fetched {len(nasdaq_stocks)} NASDAQ stocks")

    other_stocks = fetch_other_stocks()
    print(f"Fetched {len(other_stocks)} other exchange stocks")

    # Combine and dedupe by ticker
    all_stocks = {}
    for stock in nasdaq_stocks + other_stocks:
        ticker = stock['ticker']
        if ticker not in all_stocks:
            all_stocks[ticker] = stock

    stocks_list = list(all_stocks.values())
    print(f"Total unique stocks: {len(stocks_list)}")

    # Write to DynamoDB
    batch_write_stocks(stocks_list)
    print("Stock sync complete")

    return {
        'statusCode': 200,
        'body': {
            'nasdaq_count': len(nasdaq_stocks),
            'other_count': len(other_stocks),
            'total_unique': len(stocks_list)
        }
    }
