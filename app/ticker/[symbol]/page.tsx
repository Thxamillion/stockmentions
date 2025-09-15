import { Header } from "@/components/header"
import { TickerDetail } from "@/components/ticker-detail"
import { notFound } from "next/navigation"

interface TickerPageProps {
  params: {
    symbol: string
  }
}

export default function TickerPage({ params }: TickerPageProps) {
  const symbol = params.symbol.toUpperCase()

  // Basic validation - in a real app, you'd check against a list of valid tickers
  if (!symbol || symbol.length > 10) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <TickerDetail symbol={symbol} />
      </main>
    </div>
  )
}

export function generateMetadata({ params }: TickerPageProps) {
  const symbol = params.symbol.toUpperCase()
  return {
    title: `${symbol} - StockMentions`,
    description: `Track Reddit mentions and sentiment for ${symbol} stock ticker`,
  }
}
