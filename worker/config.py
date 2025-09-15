import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://stockmentions:stockmentions_dev@localhost:5432/stockmentions")

    # Reddit API
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "stockmentions:v1.0 (by u/stockmentions)")

    # Subreddits to monitor
    SUBREDDITS = os.getenv("SUBREDDITS", "stocks,investing,SecurityAnalysis,pennystocks,wallstreetbets,StockMarket,ValueInvesting").split(",")

    # Worker settings
    WORKER_INTERVAL_SECONDS = int(os.getenv("WORKER_INTERVAL_SECONDS", 60))
    MAX_POSTS_PER_FETCH = int(os.getenv("MAX_POSTS_PER_FETCH", 100))
    MAX_COMMENTS_PER_FETCH = int(os.getenv("MAX_COMMENTS_PER_FETCH", 500))

    # DD Detection settings
    DD_MIN_WORD_COUNT = int(os.getenv("DD_MIN_WORD_COUNT", 300))
    DD_SCORE_THRESHOLD = int(os.getenv("DD_SCORE_THRESHOLD", 6))

    # Rate limiting
    RATE_LIMIT_DELAY = int(os.getenv("RATE_LIMIT_DELAY", 2))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

    # Subreddit weights for DD detection
    SUBREDDIT_WEIGHTS = {
        "SecurityAnalysis": 2.0,
        "ValueInvesting": 1.8,
        "investing": 1.2,
        "financialindependence": 1.1,
        "dividends": 1.1,
        "stocks": 1.0,
        "StockMarket": 1.0,
        "pennystocks": 0.8,
        "wallstreetbets": 0.5
    }

config = Config()