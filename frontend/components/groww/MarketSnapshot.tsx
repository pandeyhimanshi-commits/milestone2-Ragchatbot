export function MarketSnapshot() {
  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-4 shadow-[var(--shadow)]">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-gray-800">Nifty 50</h3>
        <span className="text-sm font-semibold text-emerald-600">+1.24%</span>
      </div>
      <div className="mb-2 h-24 w-full">
        <svg
          className="h-full w-full"
          viewBox="0 0 240 80"
          preserveAspectRatio="none"
          aria-hidden
        >
          <defs>
            <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00d09c" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#00d09c" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path
            d="M0 60 L20 55 L50 50 L80 40 L120 30 L150 25 L180 20 L220 10 L240 5 L240 80 L0 80 Z"
            fill="url(#area)"
          />
          <path
            d="M0 60 L20 55 L50 50 L80 40 L120 30 L150 25 L180 20 L220 10 L240 5"
            fill="none"
            stroke="#00d09c"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      </div>
      <div className="space-y-1 text-xs text-gray-600">
        <p>
          <span className="text-gray-500">Current Value: </span>
          <span className="font-medium text-gray-800">22,453.80</span>
        </p>
        <p>
          <span className="text-gray-500">Volume: </span>
          <span className="font-medium text-gray-800">314.5M</span>
        </p>
      </div>
      <button
        type="button"
        className="mt-4 w-full rounded-xl border-2 border-[#00d09c] py-2.5 text-sm font-semibold text-[#00d09c] transition hover:bg-[#e8fcf7]"
      >
        Full Market View
      </button>
    </div>
  );
}
