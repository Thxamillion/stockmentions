"""
Reddit Fetch Lambda
Fetches new posts from target subreddits and sends them to SQS for processing.
"""

import os
import json
import boto3
import praw
from datetime import datetime, timezone

# AWS clients
ssm = boto3.client('ssm')
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

metadata_table = dynamodb.Table(os.environ['METADATA_TABLE'])
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']
TARGET_SUBREDDITS = os.environ['TARGET_SUBREDDITS'].split(',')


def get_reddit_credentials():
    """Fetch Reddit API credentials from SSM Parameter Store."""
    client_id_param = os.environ['REDDIT_CLIENT_ID_PARAM']
    client_secret_param = os.environ['REDDIT_CLIENT_SECRET_PARAM']

    response = ssm.get_parameters(
        Names=[client_id_param, client_secret_param],
        WithDecryption=True
    )

    params = {p['Name']: p['Value'] for p in response['Parameters']}

    return {
        'client_id': params[client_id_param],
        'client_secret': params[client_secret_param]
    }


def get_last_fetch_time(subreddit):
    """Get the last fetch timestamp for a subreddit."""
    try:
        response = metadata_table.get_item(
            Key={'key': f'last_fetch_{subreddit}'}
        )
        if 'Item' in response:
            return float(response['Item']['timestamp'])
    except Exception as e:
        print(f"Error getting last fetch time for {subreddit}: {e}")

    # Default to 1 hour ago if no previous fetch
    return datetime.now(timezone.utc).timestamp() - 3600


def set_last_fetch_time(subreddit, timestamp):
    """Update the last fetch timestamp for a subreddit."""
    try:
        metadata_table.put_item(Item={
            'key': f'last_fetch_{subreddit}',
            'timestamp': str(timestamp),
            'updated_at': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        print(f"Error setting last fetch time for {subreddit}: {e}")


def send_to_sqs(posts):
    """Send posts to SQS queue in batches."""
    # SQS batch limit is 10 messages
    for i in range(0, len(posts), 10):
        batch = posts[i:i+10]
        entries = [
            {
                'Id': str(idx),
                'MessageBody': json.dumps(post)
            }
            for idx, post in enumerate(batch)
        ]

        try:
            sqs.send_message_batch(
                QueueUrl=SQS_QUEUE_URL,
                Entries=entries
            )
        except Exception as e:
            print(f"Error sending batch to SQS: {e}")


def lambda_handler(event, context):
    """Main Lambda handler."""
    print(f"Starting Reddit fetch for subreddits: {TARGET_SUBREDDITS}")

    # Get Reddit credentials
    creds = get_reddit_credentials()

    # Initialize PRAW
    reddit = praw.Reddit(
        client_id=creds['client_id'],
        client_secret=creds['client_secret'],
        user_agent='stock-mentions:v1.0 (by /u/stock-mentions-bot)'
    )
    reddit.read_only = True

    total_posts = 0

    for subreddit_name in TARGET_SUBREDDITS:
        print(f"Fetching from r/{subreddit_name}")

        last_fetch = get_last_fetch_time(subreddit_name)
        latest_timestamp = last_fetch
        posts_to_send = []

        try:
            subreddit = reddit.subreddit(subreddit_name)

            for submission in subreddit.new(limit=100):
                # Skip posts older than last fetch
                if submission.created_utc <= last_fetch:
                    continue

                # Track latest timestamp
                if submission.created_utc > latest_timestamp:
                    latest_timestamp = submission.created_utc

                post_data = {
                    'post_id': submission.id,
                    'subreddit': subreddit_name,
                    'title': submission.title,
                    'author': str(submission.author) if submission.author else '[deleted]',
                    'upvotes': submission.score,
                    'url': f'https://reddit.com{submission.permalink}',
                    'created_utc': submission.created_utc
                }

                posts_to_send.append(post_data)

            print(f"Found {len(posts_to_send)} new posts in r/{subreddit_name}")

            if posts_to_send:
                send_to_sqs(posts_to_send)
                total_posts += len(posts_to_send)

            # Update last fetch time
            if latest_timestamp > last_fetch:
                set_last_fetch_time(subreddit_name, latest_timestamp)

        except Exception as e:
            print(f"Error fetching from r/{subreddit_name}: {e}")

    print(f"Total posts sent to SQS: {total_posts}")

    return {
        'statusCode': 200,
        'body': {
            'subreddits_processed': len(TARGET_SUBREDDITS),
            'posts_fetched': total_posts
        }
    }
