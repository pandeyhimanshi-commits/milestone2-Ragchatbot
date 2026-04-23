import { BarChart3, FileText, Rocket, Building2 } from "lucide-react";

const cards = [
  {
    title: "Portfolio Analysis",
    body: "Analyze my current stock allocation and suggest rebalancing.",
    icon: BarChart3,
  },
  {
    title: "Tax Harvest",
    body: "Find opportunities for tax-loss harvesting.",
    icon: FileText,
  },
  {
    title: "Market Insights",
    body: "What are the top 5 performing mid-cap stocks this week?",
    icon: Rocket,
  },
  {
    title: "Mutual Fund SIP",
    body: "Compare top-rated index funds for a 10-year investment horizon.",
    icon: Building2,
  },
] as const;

export function QuickActionGrid() {
  return (
    <div className="mt-2 grid w-full max-w-3xl grid-cols-1 gap-4 sm:grid-cols-2">
      {cards.map((c) => {
        const Icon = c.icon;
        return (
          <button
            key={c.title}
            type="button"
            className="group flex flex-col rounded-2xl border border-gray-100 bg-white p-4 text-left shadow-[var(--shadow)] transition hover:border-[#c5f2e6] hover:shadow-[var(--shadow-lg)]"
          >
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-[#e8fcf7] text-[#00d09c] transition group-hover:bg-[#d4f5ec]">
              <Icon className="h-5 w-5" strokeWidth={2} />
            </div>
            <h3 className="text-sm font-semibold text-gray-900">{c.title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-gray-500">{c.body}</p>
          </button>
        );
      })}
    </div>
  );
}
