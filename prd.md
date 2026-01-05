# Stock Mentions - Technical Specification

## Overview

**Project Name:** Stock Mentions  
**Goal:** Track stock ticker mentions across Reddit communities and display trends on a public dashboard.  
**Focus:** AWS services (staying within free tier)

### Target Subreddits
- r/wallstreetbets
- r/stocks
- r/investing
- r/stockmarket
- r/options

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA INGESTION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  NASDAQ/NYSE List ──► EventBridge (every 3 days) ──► Lambda ──► DynamoDB   │
│                                                          (stocks table)     │
│                                                                             │
│  Reddit API ──► EventBridge (hourly) ──► Lambda ──► SQS ──► Lambda ──►     │
│                                         (fetch)           (process)         │
│                                                                  │          │
│                                                                  ▼          │
│                                                           DynamoDB          │
│                                                        (mentions table)     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  API Gateway (HTTP API) ──► Lambda ──► DynamoDB                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  React + Vite (static build) ──► S3 ──► CloudFront                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## AWS Services

| Service | Purpose | Free Tier Limit |
|---------|---------|-----------------|
| Lambda | All compute (ingestion, processing, API) | 1M requests, 400K GB-sec/month |
| DynamoDB | Data storage | 25 GB, 25 RCU/WCU |
| API Gateway | HTTP API for frontend | 1M calls/month |
| EventBridge | Scheduled triggers (cron) | Free |
| SQS | Queue between fetch and process | 1M requests/month |
| S3 | Static site hosting | 5 GB storage |
| CloudFront | CDN for frontend | 1 TB transfer/month |

---

## Data Models

### Stocks Table

**Table Name:** `stock-mentions-stocks`  
**Partition Key:** `ticker` (String)

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "exchange": "NASDAQ",
  "sector": "Technology",
  "updated_at": "2024-01-15T00:00:00Z"
}
```

**Access Patterns:**
- Get stock by ticker (for validation during mention processing)
- Scan all stocks (for ticker matching regex generation)

---

### Mentions Table

**Table Name:** `stock-mentions-mentions`  
**Partition Key:** `ticker` (String)  
**Sort Key:** `timestamp#post_id` (String)

**Post Mention:**
```json
{
  "ticker": "AAPL",
  "timestamp_post_id": "2024-01-15T14:30:00Z#abc123",
  "subreddit": "wallstreetbets",
  "post_id": "abc123",
  "post_title": "AAPL to the moon!",
  "post_body": "I think AAPL is going to surge...",
  "author": "u/someone",
  "upvotes": 150,
  "url": "https://reddit.com/r/wallstreetbets/...",
  "created_utc": 1705329000,
  "source_type": "post"
}
```

**Comment Mention:**
```json
{
  "ticker": "AAPL",
  "timestamp_post_id": "2024-01-15T14:35:00Z#def456",
  "subreddit": "wallstreetbets",
  "post_id": "abc123",
  "comment_id": "def456",
  "comment_body": "Agreed, AAPL looks strong",
  "parent_id": "abc123",
  "author": "u/trader123",
  "upvotes": 45,
  "url": "https://reddit.com/r/wallstreetbets/.../def456",
  "created_utc": 1705329300,
  "source_type": "comment"
}
```

**GSI - By Subreddit:**
- Partition Key: `subreddit`
- Sort Key: `timestamp#post_id`

**Access Patterns:**
- Get mentions for a ticker (sorted by time)
- Get mentions for a subreddit (sorted by time)
- Query mentions in a time range

---

## API Endpoints

Base URL: `https://{api-id}.execute-api.{region}.amazonaws.com`

### GET /trending

Returns top mentioned tickers in the last 24 hours.

**Response:**
```json
{
  "period": "24h",
  "data": [
    { "ticker": "NVDA", "mentions": 142, "change": "+45%" },
    { "ticker": "TSLA", "mentions": 98, "change": "-12%" },
    { "ticker": "AAPL", "mentions": 76, "change": "+8%" }
  ]
}
```

### GET /ticker/{symbol}

Returns mention history for a specific ticker.

**Query Params:**
- `period`: `24h` | `7d` | `30d` (default: `24h`)

**Response:**
```json
{
  "ticker": "NVDA",
  "company_name": "NVIDIA Corporation",
  "period": "24h",
  "total_mentions": 142,
  "by_subreddit": {
    "wallstreetbets": 89,
    "stocks": 32,
    "investing": 21
  },
  "recent_posts": [
    {
      "subreddit": "wallstreetbets",
      "title": "NVDA earnings play",
      "upvotes": 234,
      "url": "https://...",
      "timestamp": "2024-01-15T14:30:00Z"
    }
  ]
}
```

### GET /subreddit/{name}

Returns top tickers for a specific subreddit.

**Response:**
```json
{
  "subreddit": "wallstreetbets",
  "period": "24h",
  "top_tickers": [
    { "ticker": "NVDA", "mentions": 89 },
    { "ticker": "TSLA", "mentions": 67 }
  ]
}
```

---

## Lambda Functions

### 1. stock-sync

**Trigger:** EventBridge (every 3 days at 6 AM UTC)
**Purpose:** Fetch NASDAQ/NYSE stock list and update DynamoDB
**Runtime:** Python 3.12
**Timeout:** 5 minutes
**Memory:** 256 MB

**Data Sources:**
- NASDAQ-listed stocks: `ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt`
- Other exchanges (NYSE, NYSE American, NYSE Arca, BATS, etc.): `ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt`

---

### 2. reddit-fetch

**Trigger:** EventBridge (every hour)  
**Purpose:** Poll Reddit API for new posts using PRAW, send to SQS  
**Runtime:** Python 3.12  
**Timeout:** 1 minute  
**Memory:** 128 MB  
**Dependencies:** `praw`

**Logic:**
1. Initialize PRAW client with credentials from SSM
2. For each subreddit, fetch new posts (limit 100)
3. Filter to posts created since last run
4. Send each post to SQS for processing

**Example:**
```python
import praw

reddit = praw.Reddit(
    client_id="...",
    client_secret="...",
    user_agent="stock-mentions:v1.0 (by /u/yourusername)"
)

for submission in reddit.subreddit("wallstreetbets").new(limit=100):
    # process submission
```

---

### 3. mention-processor

**Trigger:** SQS queue  
**Purpose:** Match tickers in post titles, store mentions  
**Runtime:** Python 3.12  
**Timeout:** 30 seconds  
**Memory:** 128 MB

**Logic:**
1. Receive post from SQS
2. Load ticker list from DynamoDB (or cache)
3. Normalize text (strip `$` symbols), then exact match against known tickers
4. For each match, write to mentions table

---

### 4. api-handler

**Trigger:** API Gateway  
**Purpose:** Handle all API requests  
**Runtime:** Python 3.12  
**Timeout:** 10 seconds  
**Memory:** 128 MB

---

## Reddit API Setup

### Library
Using **PRAW** (Python Reddit API Wrapper) - handles OAuth, rate limiting, and pagination automatically.

```bash
pip install praw
```

### App Registration
1. Go to https://www.reddit.com/prefs/apps
2. Create "script" type application
3. Note: client_id (under app name), client_secret

### PRAW Configuration
```python
import praw

reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    user_agent="stock-mentions:v1.0 (by /u/yourusername)"
)

# Read-only mode (no username/password needed for public data)
reddit.read_only = True
```

### Rate Limits
- PRAW handles rate limiting automatically
- ~60 requests/minute with OAuth
- User-Agent required (PRAW sets this from config)

### Secrets Storage
Store in AWS SSM Parameter Store (SecureString):
- `/stock-mentions/reddit_client_id`
- `/stock-mentions/reddit_client_secret`

---

## Implementation Plan

### Phase 1: Foundation
- [ ] Set up AWS account/credentials
- [ ] Create DynamoDB tables
- [ ] Deploy stock-sync Lambda
- [ ] Manually trigger and verify stock data

### Phase 2: Reddit Ingestion
- [ ] Register Reddit app
- [ ] Store credentials in SSM Parameter Store
- [ ] Deploy reddit-fetch Lambda
- [ ] Deploy mention-processor Lambda
- [ ] Set up SQS queue
- [ ] Configure EventBridge hourly trigger
- [ ] Test end-to-end ingestion

### Phase 3: API
- [ ] Deploy api-handler Lambda
- [ ] Create API Gateway HTTP API
- [ ] Implement /trending endpoint
- [ ] Implement /ticker/{symbol} endpoint
- [ ] Implement /subreddit/{name} endpoint
- [ ] Test all endpoints

### Phase 4: Frontend
- [ ] Scaffold React + Vite project
- [ ] Build dashboard UI (trending list, search, charts)
- [ ] Connect to API
- [ ] Deploy to S3 + CloudFront

### Phase 5: Polish
- [ ] Add error handling and retries
- [ ] Set up CloudWatch alarms
- [ ] Optimize DynamoDB queries
- [ ] Add caching if needed

---

## Future Enhancements (V2)

- **Company name matching** - Match "Apple" not just "AAPL"
- **Sentiment analysis** - AWS Comprehend on post titles
- **Comments parsing** - Not just post titles
- **Price correlation** - Show stock price alongside mention trends
- **Alerts** - SNS notifications for mention spikes
- **Historical data** - Charts over longer periods
- **More sources** - Twitter/X, StockTwits, Discord

---

## File Structure (Suggested)

```
stock-mentions/
├── infrastructure/
│   ├── main.tf                # Main Terraform config
│   ├── variables.tf           # Input variables
│   ├── outputs.tf             # Output values
│   ├── dynamodb.tf            # DynamoDB tables
│   ├── lambda.tf              # Lambda functions
│   ├── api-gateway.tf         # API Gateway
│   ├── eventbridge.tf         # Scheduled triggers
│   ├── sqs.tf                 # SQS queue
│   ├── s3-cloudfront.tf       # Frontend hosting
│   ├── iam.tf                 # IAM roles/policies
│   └── terraform.tfvars       # Variable values (gitignored)
├── lambdas/
│   ├── stock-sync/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── reddit-fetch/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── mention-processor/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── api-handler/
│       ├── handler.py
│       └── requirements.txt
├── scripts/
│   └── deploy-lambdas.sh      # Zip and upload Lambda code
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## Deployment

Using Terraform for infrastructure-as-code:

```bash
# Initialize Terraform
cd infrastructure
terraform init

# Preview changes
terraform plan

# Deploy infrastructure
terraform apply

# Deploy Lambda code (after infra exists)
./scripts/deploy-lambdas.sh

# Deploy frontend
cd frontend
npm run build
aws s3 sync dist/ s3://stock-mentions-frontend --delete
aws cloudfront create-invalidation --distribution-id XXXXX --paths "/*"
```

---

## Local Development

```bash
# Test Lambda locally (using python-lambda-local or docker)
cd lambdas/stock-sync
pip install -r requirements.txt
python -c "from handler import lambda_handler; lambda_handler({}, None)"

# Frontend dev
cd frontend
npm run dev
```

---

## Cost Estimate (Monthly)

With hourly polling and moderate traffic:

| Service | Estimated Usage | Cost |
|---------|-----------------|------|
| Lambda | ~2,000 invocations | $0 (free tier) |
| DynamoDB | <1 GB, low RCU/WCU | $0 (free tier) |
| API Gateway | ~10,000 requests | $0 (free tier) |
| S3 | ~10 MB | $0 (free tier) |
| CloudFront | ~1 GB transfer | $0 (free tier) |
| **Total** | | **$0** |

*Note: Free tier eligible for 12 months on new AWS accounts*

---

## Notes

- Ticker matching MVP: Normalize text (strip `$`), then exact match against known tickers in DB
- Avoid false positives: Skip common words that are also tickers (A, IT, ARE, BE, FOR, etc.)

- PRAW in Lambda: Include `praw` in requirements.txt, package with Lambda zip
- Terraform state: Use S3 backend for remote state (recommended for real projects)
- Lambda packaging: Zip handler.py + dependencies, upload to S3, reference in Terraform