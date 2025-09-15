"use client"

import { useState, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Info, TrendingUp, TrendingDown, Filter } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import Link from "next/link"

type TimeRange = "daily" | "weekly" | "monthly"

interface TickerData {
  rank: number
  ticker: string
  posts: number
  comments: number
  change?: number
}

interface SubredditData {
  [key: string]: TickerData[]
}

interface ApiResponse {
  tickers?: TickerData[]
  subreddits?: SubredditData
}

function getTickerColor(ticker: string): string {
  const colors = [
    "bg-emerald-500", // Primary brand color
    "bg-slate-500", // Neutral
    "bg-blue-500", // Accent
  ]
  const hash = ticker.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return colors[hash % colors.length]
}

function formatNumber(num: number): string {
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}k`
  }
  return num.toString()
}

interface LeaderboardTableProps {
  data: TickerData[]
  title: string
  timeRange: TimeRange
}

function LeaderboardTable({ data, title, timeRange }: LeaderboardTableProps) {
  const timeRangeLabel = timeRange.charAt(0).toUpperCase() + timeRange.slice(1)

  return (
    <Card className="flex-1">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="text-lg font-semibold">
          {title} ({timeRangeLabel.slice(0, 3)})
        </CardTitle>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <Info className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Ranks by total Reddit activity for the selected range.</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-hidden">
          <table className="w-full">
            <thead className="sticky top-0 bg-muted/50">
              <tr className="border-b text-xs font-medium text-muted-foreground">
                <th className="text-right py-3 px-4 w-16">Rank</th>
                <th className="text-left py-3 px-4">Ticker</th>
                <th className="text-right py-3 px-4">Posts</th>
                <th className="text-right py-3 px-4">Comments</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item, index) => (
                <tr
                  key={item.ticker}
                  className={`border-b hover:bg-muted/50 transition-colors ${
                    index % 2 === 0 ? "bg-background" : "bg-muted/20"
                  }`}
                >
                  <td className="text-right py-3 px-4 text-sm font-medium">{item.rank}</td>
                  <td className="py-3 px-4">
                    <Link href={`/ticker/${item.ticker.toLowerCase()}`}>
                      <Badge
                        variant="secondary"
                        className={`${getTickerColor(item.ticker)} text-white hover:opacity-80 cursor-pointer`}
                      >
                        {item.ticker}
                      </Badge>
                    </Link>
                  </td>
                  <td className="text-right py-3 px-4 text-sm">{formatNumber(item.posts)}</td>
                  <td className="text-right py-3 px-4 text-sm flex items-center justify-end gap-1">
                    {formatNumber(item.comments)}
                    {item.change && (
                      <span
                        className={`text-xs flex items-center ${item.change > 0 ? "text-green-500" : "text-red-500"}`}
                      >
                        {item.change > 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                        {Math.abs(item.change)}%
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export function TickerMentions() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [timeRange, setTimeRange] = useState<TimeRange>("daily")
  const [sortBy, setSortBy] = useState<"posts" | "comments" | "change">("posts")
  const [data, setData] = useState<SubredditData>({
    overall: [],
    pennystocks: [],
    TheRaceTo10Million: []
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const rangeParam = searchParams.get("range") as TimeRange
    if (rangeParam && ["daily", "weekly", "monthly"].includes(rangeParam)) {
      setTimeRange(rangeParam)
    }
  }, [searchParams])

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        // Fetch overall mentions
        const overallResponse = await fetch(`/api/mentions?timeRange=${timeRange}&subreddit=all`)
        const overallData = await overallResponse.json()

        // Fetch subreddit-specific data
        const subredditResponse = await fetch(`/api/subreddits?timeRange=${timeRange}`)
        const subredditData = await subredditResponse.json()

        setData({
          overall: overallData.tickers || [],
          pennystocks: subredditData.subreddits?.pennystocks || [],
          TheRaceTo10Million: subredditData.subreddits?.TheRaceTo10Million || []
        })
      } catch (err) {
        console.error('Failed to fetch data:', err)
        setError('Failed to load ticker data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [timeRange])

  const handleTimeRangeChange = (newRange: TimeRange) => {
    setTimeRange(newRange)
    const params = new URLSearchParams(searchParams.toString())
    params.set("range", newRange)
    router.push(`/?${params.toString()}`, { scroll: false })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Ticker Mentions</h1>
        <p className="text-muted-foreground">Track the most talked about stock tickers across Reddit communities</p>
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">Time Range:</span>
            <div className="flex rounded-lg border p-1">
              {(["daily", "weekly", "monthly"] as const).map((range) => (
                <Button
                  key={range}
                  variant={timeRange === range ? "default" : "ghost"}
                  size="sm"
                  onClick={() => handleTimeRangeChange(range)}
                  className="capitalize"
                >
                  {range}
                </Button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Sort by:</span>
          <Select value={sortBy} onValueChange={(value: "posts" | "comments" | "change") => setSortBy(value)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="posts">Posts</SelectItem>
              <SelectItem value="comments">Comments</SelectItem>
              <SelectItem value="change">Change</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Leaderboards */}
      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="flex-1">
              <CardHeader>
                <div className="h-6 bg-muted rounded animate-pulse" />
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[1, 2, 3, 4, 5].map((j) => (
                    <div key={j} className="h-8 bg-muted rounded animate-pulse" />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-8">
          <p className="text-red-500">{error}</p>
          <Button onClick={() => window.location.reload()} className="mt-4">
            Retry
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <LeaderboardTable data={data.overall} title="Overall Top 10" timeRange={timeRange} />
          <LeaderboardTable data={data.pennystocks} title="r/pennystocks" timeRange={timeRange} />
          <LeaderboardTable data={data.TheRaceTo10Million} title="r/TheRaceTo10Million" timeRange={timeRange} />
        </div>
      )}
    </div>
  )
}
