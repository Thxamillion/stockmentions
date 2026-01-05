# Stock Mentions - Implementation Plan

## Overview
Build a Reddit stock mention tracker with AWS serverless backend and React + Vite frontend.
Development will proceed in parallel tracks.

---

## Project Structure

```
stock-mentions/
├── infrastructure/          # Terraform IaC
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── dynamodb.tf
│   ├── lambda.tf
│   ├── api-gateway.tf
│   ├── eventbridge.tf
│   ├── sqs.tf
│   ├── s3-cloudfront.tf
│   └── iam.tf
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
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── scripts/
│   └── deploy-lambdas.sh
└── prd.md
```

---

## Backend Work

### Phase B1: Infrastructure Foundation [COMPLETE]
1. **Terraform setup**
   - [x] `main.tf` - AWS provider, backend config (S3 for state)
   - [x] `variables.tf` - Region, environment, naming prefix
   - [x] `iam.tf` - Lambda execution roles with DynamoDB, SQS, SSM permissions

2. **DynamoDB tables** (`dynamodb.tf`)
   - [x] `stock-mentions-stocks` table (PK: ticker)
   - [x] `stock-mentions-mentions` table (PK: ticker, SK: timestamp#post_id)
   - [x] GSI on mentions: by subreddit

3. **SQS queue** (`sqs.tf`)
   - [x] `stock-mentions-posts` queue for Reddit posts

### Phase B2: Stock Sync Lambda [COMPLETE]
1. **Lambda function** (`lambdas/stock-sync/handler.py`)
   - [x] Fetch from both NASDAQ FTP URLs:
     - `nasdaqlisted.txt`
     - `otherlisted.txt`
   - [x] Parse pipe-delimited files
   - [x] Batch write to DynamoDB stocks table
   - [x] Handle duplicates gracefully

2. **EventBridge rule** (`eventbridge.tf`)
   - [x] Schedule: every 3 days at 6 AM UTC
   - [x] Target: stock-sync Lambda

3. **Terraform Lambda resource** (`lambda.tf`)
   - [x] Python 3.12 runtime
   - [x] 256 MB memory, 5 min timeout
   - [x] Environment variables for table name

### Phase B3: Reddit Ingestion Pipeline [COMPLETE]
1. **SSM Parameters** (manual or Terraform)
   - [ ] `/stock-mentions/reddit_client_id`
   - [ ] `/stock-mentions/reddit_client_secret`

2. **reddit-fetch Lambda** (`lambdas/reddit-fetch/handler.py`)
   - [x] Initialize PRAW client from SSM credentials
   - [x] Loop through target subreddits
   - [x] Fetch new posts (limit 100 each)
   - [x] Track last fetch timestamp in DynamoDB
   - [x] Send posts to SQS

3. **mention-processor Lambda** (`lambdas/mention-processor/handler.py`)
   - [x] Triggered by SQS
   - [x] Load ticker set from DynamoDB (cache in memory)
   - [x] Normalize text (strip $, uppercase)
   - [x] Exact match against ticker set
   - [x] Skip common-word tickers (A, I, IT, BE, FOR, AT, ON, etc.)
   - [x] Write matches to mentions table

4. **EventBridge rule** for hourly reddit-fetch trigger
   - [x] Configured in `eventbridge.tf`

### Phase B4: API Layer [COMPLETE]
1. **api-handler Lambda** (`lambdas/api-handler/handler.py`)
   - [x] Route parsing for:
     - `GET /trending` - Top tickers last 24h
     - `GET /ticker/{symbol}` - Ticker detail + mentions
     - `GET /subreddit/{name}` - Top tickers for subreddit
   - [x] Query DynamoDB with appropriate filters
   - [x] Return JSON responses

2. **API Gateway** (`api-gateway.tf`)
   - [x] HTTP API (cheaper than REST API)
   - [x] Routes pointing to api-handler Lambda
   - [x] CORS configuration for frontend

### Phase B5: Deployment [IN PROGRESS]
1. **Lambda packaging script** (`scripts/deploy-lambdas.sh`)
   - [x] Install dependencies into package dir
   - [x] Zip with handler.py
   - [x] Upload to S3

2. **Test end-to-end flow**
   - [ ] Run `terraform init` and `terraform apply`
   - [ ] Set up Reddit API credentials in SSM
   - [ ] Manually trigger stock-sync
   - [ ] Manually trigger reddit-fetch
   - [ ] Verify mentions in DynamoDB
   - [ ] Test API endpoints

---

## Frontend Work

### Phase F1: Project Setup
1. **Scaffold React + Vite + TypeScript**
   ```bash
   cd frontend
   npm create vite@latest . -- --template react-ts
   npm install
   ```

2. **Install dependencies**
   - `axios` or `fetch` wrapper for API calls
   - `recharts` or `chart.js` for charts
   - `tailwindcss` for styling
   - `react-router-dom` for routing

3. **Configure Vite**
   - API proxy for local development
   - Build output for S3

### Phase F2: Core Components
1. **Layout components**
   - `Header` - Logo, navigation
   - `Layout` - Page wrapper

2. **Dashboard page** (`/`)
   - `TrendingTable` - Top 20 tickers with mention counts, % change
   - `SubredditTabs` - Filter by subreddit
   - Auto-refresh every 5 minutes

3. **Ticker detail page** (`/ticker/:symbol`)
   - `TickerHeader` - Symbol, company name, total mentions
   - `MentionChart` - Line chart of mentions over time
   - `SubredditBreakdown` - Pie/bar chart by subreddit
   - `RecentPosts` - List of recent Reddit posts with links

4. **Subreddit page** (`/subreddit/:name`)
   - Top tickers for that subreddit
   - Recent activity

### Phase F3: API Integration
1. **API client** (`src/api/client.ts`)
   - Base URL configuration (env variable)
   - Typed fetch functions:
     - `getTrending()`
     - `getTicker(symbol, period)`
     - `getSubreddit(name)`

2. **React Query or SWR** (optional)
   - Caching and refetching

3. **Mock data** for development before backend is ready

### Phase F4: Polish
1. **Loading states** - Skeletons
2. **Error handling** - Error boundaries, retry
3. **Responsive design** - Mobile-friendly
4. **Dark mode** (optional)

### Phase F5: Deployment
1. **S3 bucket** for static hosting
2. **CloudFront distribution** for CDN
3. **Build and deploy script**
   ```bash
   npm run build
   aws s3 sync dist/ s3://stock-mentions-frontend --delete
   aws cloudfront create-invalidation --distribution-id XXX --paths "/*"
   ```

---

## Parallel Development Strategy

| Week | Backend | Frontend |
|------|---------|----------|
| 1 | B1 (Terraform + DynamoDB) | F1 (Project setup) |
| 1 | B2 (stock-sync Lambda) | F2 (Layout + components with mock data) |
| 2 | B3 (Reddit ingestion) | F2 continued |
| 2 | B4 (API) | F3 (Connect to real API) |
| 3 | B5 (Deploy + test) | F4 + F5 (Polish + deploy) |

---

## Files to Create

### Backend (19 files) [COMPLETE]
- [x] `infrastructure/main.tf`
- [x] `infrastructure/variables.tf`
- [x] `infrastructure/outputs.tf`
- [x] `infrastructure/dynamodb.tf`
- [x] `infrastructure/lambda.tf`
- [x] `infrastructure/api-gateway.tf`
- [x] `infrastructure/eventbridge.tf`
- [x] `infrastructure/sqs.tf`
- [x] `infrastructure/s3-cloudfront.tf`
- [x] `infrastructure/iam.tf`
- [x] `lambdas/stock-sync/handler.py`
- [x] `lambdas/stock-sync/requirements.txt`
- [x] `lambdas/reddit-fetch/handler.py`
- [x] `lambdas/reddit-fetch/requirements.txt`
- [x] `lambdas/mention-processor/handler.py`
- [x] `lambdas/mention-processor/requirements.txt`
- [x] `lambdas/api-handler/handler.py`
- [x] `lambdas/api-handler/requirements.txt`
- [x] `scripts/deploy-lambdas.sh`

### Frontend (12+ files)
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tailwind.config.js`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/TickerDetail.tsx`
- `frontend/src/pages/SubredditView.tsx`
- `frontend/src/components/Header.tsx`
- `frontend/src/components/TrendingTable.tsx`
- `frontend/src/components/MentionChart.tsx`
- `frontend/src/components/RecentPosts.tsx`

---

## Starting Point
Begin with **B1 + F1** in parallel:
- Backend: Set up Terraform files and DynamoDB tables
- Frontend: Scaffold Vite project with Tailwind
