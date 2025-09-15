"use client"

import { useState, useMemo, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { ExternalLink, Eye, Save, Grid3X3, List, Filter, X, TrendingUp, MessageSquare, Star } from "lucide-react"

interface DDPost {
  id: string
  ticker: string
  title: string
  subreddit: string
  author: string
  qualityScore: number
  confidence: number
  date: string
  url: string
  timeAgo: string
}

// Mock fallback data
const mockPosts = [
  {
    id: 1,
    ticker: "TSLA",
    sector: "Automotive",
    title: "Tesla Q4 2024 Deep Dive: Production Scaling and Margin Analysis",
    snippet:
      "After analyzing Tesla's latest production data and cost structure, I believe the company is positioned for significant margin expansion in 2025. Key factors include...",
    subreddit: "r/SecurityAnalysis",
    author: "u/DeepValueInvestor",
    age: "2h",
    upvotes: 847,
    comments: 156,
    qualityScore: 9.2,
    tags: ["Valuation", "DCF", "Earnings"],
    hasImage: true,
    content: "Full detailed analysis of Tesla's Q4 performance and forward outlook...",
  },
  {
    id: 2,
    ticker: "NVDA",
    sector: "Technology",
    title: "NVIDIA AI Moat Analysis: Why Competition Won't Catch Up Soon",
    snippet:
      "Despite increasing competition from AMD and Intel, NVIDIA's software ecosystem creates an insurmountable moat. Here's why CUDA dominance will persist...",
    subreddit: "r/investing",
    author: "u/TechAnalyst99",
    age: "4h",
    upvotes: 623,
    comments: 89,
    qualityScore: 8.7,
    tags: ["Moat", "Thesis", "Catalyst"],
    hasImage: false,
    content: "Comprehensive analysis of NVIDIA's competitive advantages...",
  },
  {
    id: 3,
    ticker: "AAPL",
    sector: "Technology",
    title: "Apple Services Revenue: The Hidden Growth Engine",
    snippet:
      "While iPhone sales get all the attention, Apple's services segment is quietly becoming the most valuable part of the business. My analysis shows...",
    subreddit: "r/stocks",
    author: "u/AppleWatcher",
    age: "6h",
    upvotes: 445,
    comments: 67,
    qualityScore: 8.1,
    tags: ["Thesis", "Valuation"],
    hasImage: true,
    content: "Deep dive into Apple's services revenue growth and margins...",
  },
  {
    id: 4,
    ticker: "AMZN",
    sector: "E-commerce",
    title: "Amazon AWS vs Azure vs GCP: Market Share Analysis 2024",
    snippet:
      "Cloud computing remains Amazon's cash cow, but competition is intensifying. My analysis of market share trends and pricing power reveals...",
    subreddit: "r/SecurityAnalysis",
    author: "u/CloudExpert",
    age: "8h",
    upvotes: 389,
    comments: 45,
    qualityScore: 7.9,
    tags: ["Risks", "Catalyst"],
    hasImage: false,
    content: "Detailed comparison of major cloud providers and market dynamics...",
  },
]

const subreddits = ["r/stocks", "r/investing", "r/pennystocks", "r/SecurityAnalysis", "r/wallstreetbets"]
const tags = ["Thesis", "Valuation", "Risks", "Catalyst", "Earnings", "Short thesis", "DCF", "Moat"]
const timeRanges = ["Daily", "Weekly", "Monthly", "YTD", "Custom"]
const sortOptions = ["Relevance", "Newest", "Quality Score", "Upvotes", "Comments"]

export function DueDiligenceContent() {
  const [viewMode, setViewMode] = useState<"card" | "list">("card")
  const [selectedTickers, setSelectedTickers] = useState<string[]>([])
  const [selectedSubreddits, setSelectedSubreddits] = useState<string[]>([])
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [timeRange, setTimeRange] = useState("Weekly")
  const [sortBy, setSortBy] = useState("Relevance")
  const [tickerSearch, setTickerSearch] = useState("")
  const [selectedPost, setSelectedPost] = useState<(typeof mockPosts)[0] | null>(null)
  const [posts, setPosts] = useState<DDPost[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchPosts = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await fetch('/api/due-diligence')
        const data = await response.json()
        setPosts(data.posts || [])
      } catch (err) {
        console.error('Failed to fetch DD posts:', err)
        setError('Failed to load due diligence posts')
      } finally {
        setLoading(false)
      }
    }

    fetchPosts()
  }, [])

  const filteredPosts = useMemo(() => {
    const postsToFilter = posts.length > 0 ? posts : mockPosts
    return postsToFilter.filter((post) => {
      if (selectedTickers.length > 0 && !selectedTickers.includes(post.ticker)) return false
      if (selectedSubreddits.length > 0 && !selectedSubreddits.includes(`r/${post.subreddit}`)) return false
      return true
    })
  }, [posts, selectedTickers, selectedSubreddits])

  const toggleTicker = (ticker: string) => {
    setSelectedTickers((prev) => (prev.includes(ticker) ? prev.filter((t) => t !== ticker) : [...prev, ticker]))
  }

  const toggleSubreddit = (subreddit: string) => {
    setSelectedSubreddits((prev) =>
      prev.includes(subreddit) ? prev.filter((s) => s !== subreddit) : [...prev, subreddit],
    )
  }

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]))
  }

  const clearAllFilters = () => {
    setSelectedTickers([])
    setSelectedSubreddits([])
    setSelectedTags([])
    setTickerSearch("")
  }

  const getTickerColor = (ticker: string) => {
    const colors = ["bg-emerald-500", "bg-slate-500", "bg-blue-500"]
    const index = ticker.charCodeAt(0) % colors.length
    return colors[index]
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Due Diligence</h1>
        <p className="text-muted-foreground">
          Curated research posts and deep dives by community members. Filter by ticker, range, and source.
        </p>
      </div>

      {/* Global Controls */}
      <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
        {/* Left cluster - Filters */}
        <div className="flex flex-wrap gap-3 items-center">
          {/* Ticker Filter */}
          <div className="flex flex-wrap gap-2 items-center">
            <Input
              placeholder="Search tickers..."
              value={tickerSearch}
              onChange={(e) => setTickerSearch(e.target.value)}
              className="w-32"
            />
            {["TSLA", "NVDA", "AAPL", "AMZN", "MSFT"].map((ticker) => (
              <Button
                key={ticker}
                variant={selectedTickers.includes(ticker) ? "default" : "outline"}
                size="sm"
                onClick={() => toggleTicker(ticker)}
                className="h-8"
              >
                {ticker}
                {selectedTickers.includes(ticker) && (
                  <X
                    className="ml-1 h-3 w-3"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleTicker(ticker)
                    }}
                  />
                )}
              </Button>
            ))}
          </div>

          {/* Subreddit Filter */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" size="sm">
                <Filter className="mr-2 h-4 w-4" />
                Subreddits {selectedSubreddits.length > 0 && `(${selectedSubreddits.length})`}
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80">
              <SheetHeader>
                <SheetTitle>Filter by Subreddit</SheetTitle>
              </SheetHeader>
              <div className="space-y-4 mt-6">
                {subreddits.map((subreddit) => (
                  <div key={subreddit} className="flex items-center space-x-2">
                    <Checkbox
                      id={subreddit}
                      checked={selectedSubreddits.includes(subreddit)}
                      onCheckedChange={() => toggleSubreddit(subreddit)}
                    />
                    <Label htmlFor={subreddit}>{subreddit}</Label>
                  </div>
                ))}
              </div>
            </SheetContent>
          </Sheet>

          {/* Time Range */}
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {timeRanges.map((range) => (
                <SelectItem key={range} value={range}>
                  {range}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Right cluster - Sort and View */}
        <div className="flex gap-3 items-center">
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {sortOptions.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as "card" | "list")}>
            <TabsList>
              <TabsTrigger value="card">
                <Grid3X3 className="h-4 w-4" />
              </TabsTrigger>
              <TabsTrigger value="list">
                <List className="h-4 w-4" />
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {/* Tag Filters */}
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <Button
            key={tag}
            variant={selectedTags.includes(tag) ? "default" : "outline"}
            size="sm"
            onClick={() => toggleTag(tag)}
            className="h-7 text-xs"
          >
            {tag}
          </Button>
        ))}
        {(selectedTickers.length > 0 || selectedSubreddits.length > 0 || selectedTags.length > 0) && (
          <Button variant="ghost" size="sm" onClick={clearAllFilters} className="h-7 text-xs">
            Clear all
          </Button>
        )}
      </div>

      {/* Main Content */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="flex gap-2 mb-2">
                  <div className="h-5 bg-muted rounded w-12"></div>
                  <div className="h-5 bg-muted rounded w-16"></div>
                </div>
                <div className="h-6 bg-muted rounded"></div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="h-12 bg-muted rounded"></div>
                <div className="h-4 bg-muted rounded"></div>
                <div className="h-4 bg-muted rounded"></div>
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
      ) : viewMode === "card" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPosts.map((post) => (
            <Card key={post.id} className="group hover:shadow-lg transition-all duration-200 hover:-translate-y-1">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2 mb-2">
                  <Badge className={`${getTickerColor(post.ticker)} text-white`}>{post.ticker}</Badge>
                  {'subreddit' in post && (
                    <Badge variant="secondary" className="text-xs">
                      r/{post.subreddit}
                    </Badge>
                  )}
                </div>
                <h3 className="font-semibold line-clamp-2 leading-tight">{post.title}</h3>
              </CardHeader>
              <CardContent className="space-y-4">
                {'snippet' in post && (
                  <p className="text-sm text-muted-foreground line-clamp-3">{post.snippet}</p>
                )}

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{'subreddit' in post ? post.subreddit : `r/${post.subreddit}`}</span>
                  <span>{post.author}</span>
                  <span>{'timeAgo' in post ? post.timeAgo : post.age}</span>
                </div>

                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  {'upvotes' in post && (
                    <div className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      {post.upvotes}
                    </div>
                  )}
                  {'comments' in post && (
                    <div className="flex items-center gap-1">
                      <MessageSquare className="h-3 w-3" />
                      {post.comments}
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                    {post.qualityScore}
                  </div>
                </div>

                {'tags' in post && (
                  <div className="flex flex-wrap gap-1">
                    {post.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}

                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 bg-transparent"
                    onClick={() => window.open('url' in post ? post.url : '#', '_blank')}
                  >
                    <ExternalLink className="mr-1 h-3 w-3" />
                    Open Post
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setSelectedPost(post)}>
                    <Eye className="mr-1 h-3 w-3" />
                    Preview
                  </Button>
                  <Button size="sm" variant="outline">
                    <Save className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <div className="grid grid-cols-7 gap-4 p-4 bg-muted/50 font-medium text-sm">
            <div>Ticker</div>
            <div className="col-span-2">Title</div>
            <div>Subreddit</div>
            <div>Upvotes</div>
            <div>Quality</div>
            <div>Age</div>
          </div>
          {filteredPosts.map((post) => (
            <div key={post.id} className="grid grid-cols-7 gap-4 p-4 border-t hover:bg-muted/50 transition-colors">
              <div>
                <Badge className={`${getTickerColor(post.ticker)} text-white text-xs`}>{post.ticker}</Badge>
              </div>
              <div className="col-span-2">
                <button
                  className="text-left hover:underline font-medium line-clamp-1"
                  onClick={() => setSelectedPost(post)}
                >
                  {post.title}
                </button>
              </div>
              <div className="text-sm text-muted-foreground">{post.subreddit}</div>
              <div className="text-sm">{post.upvotes}</div>
              <div className="text-sm font-medium">{post.qualityScore}</div>
              <div className="text-sm text-muted-foreground">{post.age}</div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {filteredPosts.length === 0 && (
        <div className="text-center py-12">
          <h3 className="text-lg font-semibold mb-2">No research posts match your filters</h3>
          <p className="text-muted-foreground mb-4">Try adjusting your filters or clearing them to see more posts.</p>
          <Button onClick={clearAllFilters}>Clear Filters</Button>
        </div>
      )}

      {/* Preview Drawer */}
      <Sheet open={!!selectedPost} onOpenChange={() => setSelectedPost(null)}>
        <SheetContent className="w-full sm:max-w-2xl">
          {selectedPost && (
            <>
              <SheetHeader>
                <div className="flex items-center gap-2 mb-2">
                  <Badge className={`${getTickerColor(selectedPost.ticker)} text-white`}>{selectedPost.ticker}</Badge>
                  <Badge variant="secondary">{selectedPost.sector}</Badge>
                </div>
                <SheetTitle className="text-left">{selectedPost.title}</SheetTitle>
              </SheetHeader>

              <div className="space-y-6 mt-6">
                <div className="prose prose-sm max-w-none">
                  <p>{selectedPost.content}</p>
                </div>

                <div className="flex items-center justify-between text-sm text-muted-foreground border-t pt-4">
                  <div className="space-y-1">
                    <div>
                      {selectedPost.subreddit} • {selectedPost.author}
                    </div>
                    <div>Posted {selectedPost.age} ago</div>
                  </div>
                  <div className="text-right space-y-1">
                    <div className="flex items-center gap-4">
                      <span className="flex items-center gap-1">
                        <TrendingUp className="h-3 w-3" />
                        {selectedPost.upvotes}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" />
                        {selectedPost.comments}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                      Quality Score: {selectedPost.qualityScore}
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium">Tags</h4>
                  <div className="flex flex-wrap gap-1">
                    {selectedPost.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2 pt-4 border-t">
                  <Button className="flex-1">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Open Original
                  </Button>
                  <Button variant="outline">
                    <Save className="mr-2 h-4 w-4" />
                    Save
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
