import { ChevronRight } from "lucide-react";

export function ProTip() {
  return (
    <div className="rounded-2xl bg-[#111418] p-4 text-white shadow-[var(--shadow)]">
      <p className="text-[10px] font-semibold tracking-widest text-gray-400">PRO TIP</p>
      <p className="mt-2 text-sm leading-relaxed text-gray-200">
        Diversify your portfolio with US Tech stocks directly from Groww Assistant.
      </p>
      <a
        href="#"
        className="mt-3 inline-flex items-center gap-0.5 text-sm font-semibold text-[#00d09c] hover:underline"
      >
        Learn More
        <ChevronRight className="h-4 w-4" strokeWidth={2.5} />
      </a>
    </div>
  );
}
