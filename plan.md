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

### Phase F1: Project Setup [COMPLETE]
1. **Scaffold React + Vite + TypeScript**
   - [x] `npm create vite@latest . -- --template react-ts`

2. **Install dependencies**
   - [x] `tailwindcss` for styling
   - [x] `react-router-dom` for routing

3. **Configure Vite**
   - [x] Tailwind CSS plugin configured
   - [x] Build output for S3

### Phase F2: Core Components [COMPLETE]
1. **Layout components**
   - [x] `Wordmark` - Logo component
   - [x] `SegmentedControl` - Time range filter

2. **Dashboard page** (`/`)
   - [x] `TableCard` - Subreddit ticker tables
   - [x] `SkeletonTableCard` - Loading skeleton
   - [x] Time range filter (24h, 7d, 30d, 90d)
   - [x] Responsive grid (1/2/3 columns)

### Phase F3: API Integration [COMPLETE]
1. **API client** (`src/api/client.ts`)
   - [x] Base URL configuration (env variable)
   - [x] Typed fetch functions
   - [x] Mock data for development

### Phase F4: Polish [COMPLETE]
- [x] Loading states - Skeletons
- [x] Error handling - Retry button
- [x] Responsive design - Mobile-friendly

### Phase F5: Deployment
- [ ] S3 bucket for static hosting (defined in Terraform)
- [ ] CloudFront distribution for CDN (defined in Terraform)
- [ ] Build and deploy script

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

### Frontend (10 files) [COMPLETE]
- [x] `frontend/package.json`
- [x] `frontend/vite.config.ts`
- [x] `frontend/src/index.css` (Tailwind entry)
- [x] `frontend/src/App.tsx`
- [x] `frontend/src/api/client.ts`
- [x] `frontend/src/types/index.ts`
- [x] `frontend/src/pages/Dashboard.tsx`
- [x] `frontend/src/components/Wordmark.tsx`
- [x] `frontend/src/components/SegmentedControl.tsx`
- [x] `frontend/src/components/TableCard.tsx`
- [x] `frontend/src/components/SkeletonTableCard.tsx`

---

## Starting Point
Begin with **B1 + F1** in parallel:
- Backend: Set up Terraform files and DynamoDB tables
- Frontend: Scaffold Vite project with Tailwind
