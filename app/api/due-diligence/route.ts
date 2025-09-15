import { NextRequest, NextResponse } from 'next/server'
import pool from '@/lib/db'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    const minScore = parseFloat(searchParams.get('minScore') || '0.5')

    const query = `
      SELECT
        post_id,
        title,
        ticker,
        subreddit,
        quality_score,
        dd_confidence,
        post_date,
        url,
        author
      FROM due_diligence_posts
      WHERE dd_confidence >= $1
      ORDER BY quality_score DESC, post_date DESC
      LIMIT $2;
    `

    const result = await pool.query(query, [minScore, limit])

    const ddPosts = result.rows.map(row => ({
      id: row.post_id,
      title: row.title,
      ticker: row.ticker,
      subreddit: row.subreddit,
      qualityScore: parseFloat(row.quality_score),
      confidence: parseFloat(row.dd_confidence),
      date: row.post_date,
      url: row.url,
      author: row.author,
      timeAgo: getTimeAgo(new Date(row.post_date))
    }))

    return NextResponse.json({ posts: ddPosts })
  } catch (error) {
    console.error('Database error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch due diligence posts' },
      { status: 500 }
    )
  }
}

function getTimeAgo(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffDays > 0) {
    return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`
  } else if (diffHours > 0) {
    return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`
  } else {
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`
  }
}