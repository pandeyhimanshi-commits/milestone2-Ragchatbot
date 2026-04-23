import { Search, Bell } from "lucide-react";
import { GrowwLogo } from "./GrowwLogo";

export function TopBar() {
  return (
    <header className="flex shrink-0 items-center gap-3 border-b border-[var(--border)] bg-white px-4 py-3 md:px-6">
      <div className="flex shrink-0 items-center gap-2 md:hidden">
        <GrowwLogo className="h-9 w-9" />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[#00d09c]">Groww</p>
        </div>
      </div>
      <div className="relative min-w-0 max-w-3xl flex-1">
        <Search
          className="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-gray-400"
          strokeWidth={2}
        />
        <input
          type="search"
          placeholder="Search markets, stocks, or ask assistant..."
          className="w-full rounded-2xl border border-gray-200 bg-[#f8f9fa] py-3 pl-11 pr-4 text-sm text-gray-800 placeholder:text-gray-400 focus:border-[#00d09c] focus:outline-none focus:ring-2 focus:ring-[#00d09c]/20"
        />
      </div>
      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-full text-gray-500 transition hover:bg-gray-100"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" strokeWidth={2} />
        </button>
        <button
          type="button"
          className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full border-2 border-white bg-gradient-to-br from-[#a78bfa] to-[#7c3aed] text-xs font-bold text-white shadow-sm"
          aria-label="Profile"
        >
          H
        </button>
      </div>
    </header>
  );
}
