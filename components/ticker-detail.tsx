"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowLeft, TrendingUp, TrendingDown, MessageSquare, Users, Calendar, ExternalLink } from "lucide-react"
import Link from "next/link"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

interface TickerDetailProps {
  symbol: string
}

// Mock data for demonstration
const mockTickerData = {
  TSLA: {
    name: "Tesla, Inc.",
    price: 248.42,
    change: 12.5,
    volume: 1247,
    totalMentions: 8934,
    sentiment: "Bullish",
    topSubreddits: ["r/wallstreetbets", "r/stocks", "r/investing"],
  },
  AAPL: {
    name: "Apple Inc.",
    price: 189.84,
    change: -3.2,
    volume: 1156,
    totalMentions: 7823,
    sentiment: "Neutral",
    topSubreddits: ["r/stocks", "r/investing", "r/apple"],
  },
  NVDA: {
    name: "NVIDIA Corporation",
    price: 875.28,
    change: 24.8,
    volume: 1089,
    totalMentions: 9456,
    sentiment: "Very Bullish",
    topSubreddits: ["r/wallstreetbets", "r/stocks", "r/nvidia"],
  },
}

const mockChartData = [
  { date: "Jan 1", mentions: 120, sentiment: 0.2 },
  { date: "Jan 2", mentions: 145, sentiment: 0.4 },
  { date: "Jan 3", mentions: 189, sentiment: 0.6 },
  { date: "Jan 4", mentions: 234, sentiment: 0.3 },
  { date: "Jan 5", mentions: 267, sentiment: 0.8 },
  { date: "Jan 6", mentions: 298, sentiment: 0.7 },
  { date: "Jan 7", mentions: 312, sentiment: 0.9 },
]

const mockPosts = [
  {
    id: 1,
    title: "TSLA earnings beat expectations - bullish outlook for Q2",
    subreddit: "r/wallstreetbets",
    author: "u/investor123",
    upvotes: 1247,
    comments: 234,
    timestamp: "2 hours ago",
    sentiment: "bullish",
    isDueDiligence: true,
  },
  {
    id: 2,
    title: "Technical analysis: TSLA breaking resistance at $250",
    subreddit: "r/stocks",
    author: "u/chartmaster",
    upvotes: 892,
    comments: 156,
    timestamp: "4 hours ago",
    sentiment: "bullish",
    isDueDiligence: false,
  },
  {
    id: 3,
    title: "Concerns about TSLA production delays in China",
    subreddit: "r/investing",
    author: "u/bearish_trader",
    upvotes: 567,
    comments: 89,
    timestamp: "6 hours ago",
    sentiment: "bearish",
    isDueDiligence: true,
  },
]

function getSentimentColor(sentiment: string): string {
  switch (sentiment.toLowerCase()) {
    case "very bullish":
      return "bg-green-600 text-white"
    case "bullish":
      return "bg-green-500 text-white"
    case "neutral":
      return "bg-gray-500 text-white"
    case "bearish":
      return "bg-red-500 text-white"
    case "very bearish":
      return "bg-red-600 text-white"
    default:
      return "bg-gray-500 text-white"
  }
}

function getPostSentimentColor(sentiment: string): string {
  switch (sentiment.toLowerCase()) {
    case "bullish":
      return "text-green-500"
    case "bearish":
      return "text-red-500"
    default:
      return "text-gray-500"
  }
}

export function TickerDetail({ symbol }: TickerDetailProps) {
  const [activeTab, setActiveTab] = useState("overview")
  const tickerData = mockTickerData[symbol as keyof typeof mockTickerData] || {
    name: `${symbol} Corporation`,
    price: 0,
    change: 0,
    volume: 0,
    totalMentions: 0,
    sentiment: "Neutral",
    topSubreddits: [],
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link href="/">
        <Button variant="ghost" className="mb-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="flex items-center space-x-3">
            <h1 className="text-3xl font-bold">{symbol}</h1>
            <Badge className={getSentimentColor(tickerData.sentiment)}>{tickerData.sentiment}</Badge>
          </div>
          <p className="text-muted-foreground">{tickerData.name}</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold">${tickerData.price.toFixed(2)}</div>
          <div className={`flex items-center ${tickerData.change >= 0 ? "text-green-500" : "text-red-500"}`}>
            {tickerData.change >= 0 ? (
              <TrendingUp className="h-4 w-4 mr-1" />
            ) : (
              <TrendingDown className="h-4 w-4 mr-1" />
            )}
            {tickerData.change >= 0 ? "+" : ""}
            {tickerData.change.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Mentions</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tickerData.totalMentions.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Last 24 hours</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Post Volume</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tickerData.volume.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Posts mentioning {symbol}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Top Subreddit</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tickerData.topSubreddits[0] || "N/A"}</div>
            <p className="text-xs text-muted-foreground">Most active community</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sentiment Score</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0.72</div>
            <p className="text-xs text-muted-foreground">Bullish sentiment</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="posts">Recent Posts</TabsTrigger>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Mention Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={mockChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="mentions" stroke="hsl(var(--primary))" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="posts" className="space-y-4">
          <div className="space-y-4">
            {mockPosts.map((post) => (
              <Card key={post.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-semibold hover:text-primary cursor-pointer">{post.title}</h3>
                        {post.isDueDiligence && <Badge variant="secondary">DD</Badge>}
                        <ExternalLink className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <span>{post.subreddit}</span>
                        <span>by {post.author}</span>
                        <span>{post.timestamp}</span>
                        <span className={getPostSentimentColor(post.sentiment)}>
                          {post.sentiment.charAt(0).toUpperCase() + post.sentiment.slice(1)}
                        </span>
                      </div>
                      <div className="flex items-center space-x-4 text-sm">
                        <span className="flex items-center">
                          <TrendingUp className="h-4 w-4 mr-1" />
                          {post.upvotes}
                        </span>
                        <span className="flex items-center">
                          <MessageSquare className="h-4 w-4 mr-1" />
                          {post.comments}
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="analysis" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Due Diligence Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="rounded-lg border p-4">
                  <h4 className="font-semibold mb-2">Key Highlights</h4>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    <li>• Strong earnings beat in Q1 2024</li>
                    <li>• Production capacity expanding in Texas and Berlin</li>
                    <li>• FSD beta showing promising results</li>
                    <li>• Energy storage business growing rapidly</li>
                  </ul>
                </div>
                <div className="rounded-lg border p-4">
                  <h4 className="font-semibold mb-2">Risk Factors</h4>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    <li>• Increased competition in EV market</li>
                    <li>• Regulatory challenges in China</li>
                    <li>• Supply chain dependencies</li>
                    <li>• Valuation concerns at current levels</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
