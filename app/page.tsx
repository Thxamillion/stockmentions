import { Header } from "@/components/header"
import { TickerMentions } from "@/components/ticker-mentions"

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <TickerMentions />
      </main>
    </div>
  )
}
