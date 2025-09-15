import { NextRequest, NextResponse } from 'next/server'
import pool from '@/lib/db'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const timeRange = searchParams.get('timeRange') || 'daily'

    let timeCondition = ''
    const now = new Date()

    switch (timeRange) {
      case 'daily':
        timeCondition = `created_at >= '${new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()}'`
        break
      case 'weekly':
        timeCondition = `created_at >= '${new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString()}'`
        break
      case 'monthly':
        timeCondition = `created_at >= '${new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString()}'`
        break
      default:
        timeCondition = `created_at >= '${new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()}'`
    }

    // Get top tickers for each major subreddit
    const subreddits = ['pennystocks', 'TheRaceTo10Million', 'SecurityAnalysis', 'investing', 'stocks']
    const subredditData: { [key: string]: any[] } = {}

    for (const subreddit of subreddits) {
      const query = `
        WITH ticker_stats AS (
          SELECT
            ticker,
            COUNT(CASE WHEN source = 'post' THEN 1 END) as posts,
            COUNT(CASE WHEN source = 'comment' THEN 1 END) as comments,
            COUNT(*) as total_mentions
          FROM mentions
          WHERE ${timeCondition} AND subreddit = $1
          GROUP BY ticker
        ),
        ranked_tickers AS (
          SELECT
            ticker,
            posts,
            comments,
            total_mentions,
            ROW_NUMBER() OVER (ORDER BY total_mentions DESC) as rank
          FROM ticker_stats
        )
        SELECT * FROM ranked_tickers
        WHERE ticker NOT IN ('T', 'RE', 'HAS', 'TECH', 'LOW', 'KEY', 'PEAK', 'FAST', 'GS', 'O', 'C', 'F', 'K', 'A', 'B', 'D', 'E', 'G', 'H', 'I', 'J', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z')
        AND LENGTH(ticker) > 1
        ORDER BY rank
        LIMIT 10;
      `

      const result = await pool.query(query, [subreddit])

      subredditData[subreddit] = result.rows.map((row, index) => ({
        rank: index + 1, // Re-rank from 1-10 after filtering
        ticker: row.ticker,
        posts: parseInt(row.posts),
        comments: parseInt(row.comments),
        change: Math.random() * 40 - 20 // Mock change percentage
      }))
    }

    return NextResponse.json({ subreddits: subredditData, timeRange })
  } catch (error) {
    console.error('Database error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch subreddit data' },
      { status: 500 }
    )
  }
}