import {
  LineChart,
  Wallet,
  Eye,
  Settings,
  HelpCircle,
  MessageSquarePlus,
} from "lucide-react";
import { GrowwLogo } from "./GrowwLogo";

const nav = [
  { id: "markets", label: "Markets", icon: LineChart },
  { id: "portfolio", label: "Portfolio", icon: Wallet },
  { id: "watchlist", label: "Watchlist", icon: Eye },
] as const;

type ThreadTab = {
  id: string;
  title: string;
  preview: string;
};

type SidebarProps = {
  threads: ThreadTab[];
  activeThreadId: string;
  onSelectThread: (threadId: string) => void;
  onNewChat?: () => void;
};

export function Sidebar({ threads, activeThreadId, onSelectThread, onNewChat }: SidebarProps) {
  return (
    <aside
      className="hidden w-[280px] shrink-0 flex-col border-r border-[var(--border)] bg-white py-5 pl-4 pr-3 md:flex"
    >
      <div className="mb-6 flex items-start gap-3 pl-1">
        <GrowwLogo className="h-11 w-11" />
        <div>
          <h1 className="text-lg font-semibold leading-tight text-[#00d09c]">Groww Assistant</h1>
          <p className="text-[11px] font-medium tracking-wide text-gray-500">MODERN INVESTING</p>
        </div>
      </div>

      <button
        type="button"
        onClick={onNewChat}
        className="mb-5 flex w-full items-center justify-center gap-2 rounded-[14px] border border-[#00b98a] bg-[#00d09c] py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00c28f]"
      >
        <MessageSquarePlus className="h-4 w-4" strokeWidth={2.25} />
        New Chat
      </button>

      <section className="mb-4">
        <p className="mb-2 px-2 text-[11px] font-semibold tracking-[0.08em] text-gray-400">HISTORY</p>
        <div className="max-h-48 space-y-1 overflow-y-auto pr-1">
          {threads.map((t, index) => {
            const isActive = t.id === activeThreadId;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => onSelectThread(t.id)}
                className={`w-full rounded-xl px-3 py-2 text-left transition ${
                  isActive ? "bg-[#e8fcf7] ring-1 ring-[#c5f2e6]" : "hover:bg-gray-50"
                }`}
              >
                <p className={`truncate text-sm font-semibold ${isActive ? "text-[#00a884]" : "text-gray-700"}`}>
                  {t.title || `Thread ${index + 1}`}
                </p>
                <p className="truncate text-xs text-gray-500">{t.preview || "No messages yet"}</p>
              </button>
            );
          })}
        </div>
      </section>

      <nav className="flex flex-1 flex-col gap-0.5 border-t border-gray-100 pt-3">
        {nav.map((item) => {
          const Icon = item.icon;
          const isActive = false;
          return (
            <a
              key={item.id}
              href="#"
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                isActive
                  ? "bg-[#e8fcf7] text-[#00a884]"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              <Icon
                className={`h-[18px] w-[18px] shrink-0 ${isActive ? "text-[#00d09c]" : "text-gray-500"}`}
                strokeWidth={2}
              />
              {item.label}
            </a>
          );
        })}
      </nav>

      <div className="mt-auto space-y-0.5 border-t border-gray-100 pt-4">
        <a
          href="#"
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
        >
          <Settings className="h-[18px] w-[18px] text-gray-500" strokeWidth={2} />
          Settings
        </a>
        <a
          href="#"
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
        >
          <HelpCircle className="h-[18px] w-[18px] text-gray-500" strokeWidth={2} />
          Support
        </a>
        <div className="mt-3 flex items-center gap-3 rounded-xl px-3 py-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-[#a78bfa] to-[#7c3aed] text-xs font-bold text-white shadow-sm">
            <span>H</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-800">Himanshi</p>
            <p className="text-xs text-[#00a884]">Pro Member</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
