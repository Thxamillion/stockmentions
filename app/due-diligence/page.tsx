import { DueDiligenceContent } from "@/components/due-diligence-content"
import { Header } from "@/components/header"

export default function DueDiligencePage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <DueDiligenceContent />
      </main>
    </div>
  )
}
