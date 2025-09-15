"use client"

import type React from "react"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { Search, Moon, Sun, User, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useTheme } from "next-themes"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { useState, useRef, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"

// Mock ticker suggestions for search
const mockTickers = [
  "AAPL",
  "TSLA",
  "NVDA",
  "MSFT",
  "GOOGL",
  "AMZN",
  "META",
  "AMD",
  "GME",
  "PLTR",
  "SPY",
  "QQQ",
  "SNDL",
  "BBIG",
  "ATER",
  "MULN",
  "PROG",
  "BBBY",
  "CLOV",
  "WISH",
]

export function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const { setTheme, theme } = useTheme()
  const [searchQuery, setSearchQuery] = useState("")
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [filteredTickers, setFilteredTickers] = useState<string[]>([])
  const searchRef = useRef<HTMLDivElement>(null)

  // Filter tickers based on search query
  useEffect(() => {
    if (searchQuery.length > 0) {
      const filtered = mockTickers
        .filter((ticker) => ticker.toLowerCase().includes(searchQuery.toLowerCase()))
        .slice(0, 5)
      setFilteredTickers(filtered)
      setShowSuggestions(filtered.length > 0)
    } else {
      setShowSuggestions(false)
      setFilteredTickers([])
    }
  }, [searchQuery])

  // Close suggestions when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleSearch = (ticker?: string) => {
    const searchTicker = ticker || searchQuery
    if (searchTicker.trim()) {
      router.push(`/ticker/${searchTicker.toLowerCase()}`)
      setSearchQuery("")
      setShowSuggestions(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch()
    } else if (e.key === "Escape") {
      setShowSuggestions(false)
    }
  }

  const clearSearch = () => {
    setSearchQuery("")
    setShowSuggestions(false)
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4">
        {/* Logo and Brand */}
        <div className="flex items-center space-x-8">
          <Link href="/" className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">S</span>
            </div>
            <span className="text-xl font-bold">StockMentions</span>
          </Link>

          {/* Primary Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <Link
              href="/"
              className={cn(
                "text-sm font-medium transition-colors hover:text-primary",
                pathname === "/" ? "text-primary" : "text-muted-foreground",
              )}
            >
              Ticker Mentions
            </Link>
            <Link
              href="/due-diligence"
              className={cn(
                "text-sm font-medium transition-colors hover:text-primary",
                pathname === "/due-diligence" ? "text-primary" : "text-muted-foreground",
              )}
            >
              Due Diligence
            </Link>
          </nav>
        </div>

        {/* Search and Actions */}
        <div className="flex items-center space-x-4">
          <div className="relative hidden sm:block" ref={searchRef}>
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search ticker..."
              className="w-64 pl-10 pr-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => searchQuery.length > 0 && setShowSuggestions(true)}
            />
            {searchQuery && (
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-1 top-1/2 h-6 w-6 -translate-y-1/2"
                onClick={clearSearch}
              >
                <X className="h-3 w-3" />
              </Button>
            )}

            {/* Search Suggestions */}
            {showSuggestions && (
              <Card className="absolute top-full mt-1 w-full z-50">
                <CardContent className="p-2">
                  {filteredTickers.map((ticker) => (
                    <button
                      key={ticker}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-muted rounded-md transition-colors"
                      onClick={() => handleSearch(ticker)}
                    >
                      <span className="font-medium">{ticker}</span>
                    </button>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>

          <Button variant="ghost" size="icon" onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <User className="h-4 w-4" />
                <span className="sr-only">User menu</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>Profile</DropdownMenuItem>
              <DropdownMenuItem>Settings</DropdownMenuItem>
              <DropdownMenuItem>Sign out</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
