# StockMentions - Reddit Stock Tracker

Track the most mentioned stock tickers on Reddit with real-time data and due diligence analysis.

## Features

- **Ticker Mentions Dashboard**: Track top mentioned stocks across Reddit communities
- **Due Diligence Tracking**: Automatically detect and categorize research posts
- **Multi-timeframe Analysis**: Daily, weekly, and monthly views
- **Subreddit Filtering**: Filter by specific investment communities
- **Quality Scoring**: AI-powered ranking of due diligence content

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for Next.js development)
- Reddit API credentials

### 1. Clone and Setup

```bash
git clone <your-repo>
cd stockmentions
cp .env.example .env.local
```

### 2. Start Database

```bash
# Start Postgres + Redis
docker-compose up -d postgres redis

# Check database is ready
docker-compose logs postgres
```

### 3. Get Reddit API Credentials

1. Go to https://www.reddit.com/prefs/apps
2. Create a new "script" application
3. Add credentials to `.env.local`:
   ```
   REDDIT_CLIENT_ID="your_client_id"
   REDDIT_CLIENT_SECRET="your_client_secret"
   REDDIT_USER_AGENT="stockmentions:v1.0 (by u/yourusername)"
   ```

### 4. Run Development

```bash
# Install dependencies
npm install

# Start Next.js dev server
npm run dev
```

### 5. Start Reddit Worker (Coming Soon)

```bash
# Run the Python collector
cd worker
pip install -r requirements.txt
python collector.py
```

## Database Commands

```bash
# Start database only
docker-compose up -d postgres

# View database with pgAdmin (optional)
docker-compose --profile admin up -d pgadmin
# Visit: http://localhost:8080 (admin@stockmentions.com / admin)

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

## Architecture

- **Frontend**: Next.js 14 + Tailwind + shadcn/ui
- **Database**: PostgreSQL with materialized views
- **Worker**: Python with asyncpraw for Reddit data collection
- **Caching**: Redis for API response caching

## Database Schema

- `mentions` - Raw ticker mentions from Reddit
- `due_diligence_posts` - Classified research posts
- `mentions_hourly` - Materialized view for fast queries
- `subreddit_config` - Subreddit settings and weights

## Development

```bash
# Database schema changes
docker-compose exec postgres psql -U stockmentions -d stockmentions -f /path/to/migration.sql

# View logs
docker-compose logs postgres
docker-compose logs redis

# Refresh materialized views
docker-compose exec postgres psql -U stockmentions -d stockmentions -c "REFRESH MATERIALIZED VIEW mentions_hourly;"
```