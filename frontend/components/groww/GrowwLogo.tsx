export function GrowwLogo({ className = "h-10 w-10" }: { className?: string }) {
  return (
    <div className={`shrink-0 ${className}`}>
      <svg viewBox="0 0 100 100" className="h-full w-full" aria-hidden>
        <defs>
          <clipPath id="growwCircleSmall">
            <circle cx="50" cy="50" r="48" />
          </clipPath>
        </defs>
        <g clipPath="url(#growwCircleSmall)">
          <rect x="0" y="0" width="100" height="100" fill="#5363e7" />
          <path
            fill="#1edbb7"
            d="M-2 73 C 12 68, 22 59, 34 52 C 39 49, 44 49, 48 52 C 53 56, 58 59, 63 62 C 67 64, 71 64, 75 61 C 84 54, 92 45, 102 37 V102 H-2 Z"
          />
        </g>
        <circle cx="50" cy="50" r="48" fill="none" stroke="rgba(0,0,0,0.02)" strokeWidth="1" />
      </svg>
    </div>
  );
}

export function GrowwLogoHero({ className = "h-20 w-20" }: { className?: string }) {
  return (
    <div className={`shrink-0 ${className}`}>
      <svg viewBox="0 0 100 100" className="h-full w-full" aria-hidden>
        <defs>
          <clipPath id="growwCircleHero">
            <circle cx="50" cy="50" r="48" />
          </clipPath>
        </defs>
        <g clipPath="url(#growwCircleHero)">
          <rect x="0" y="0" width="100" height="100" fill="#5363e7" />
          <path
            fill="#1edbb7"
            d="M-2 73 C 12 68, 22 59, 34 52 C 39 49, 44 49, 48 52 C 53 56, 58 59, 63 62 C 67 64, 71 64, 75 61 C 84 54, 92 45, 102 37 V102 H-2 Z"
          />
        </g>
        <circle cx="50" cy="50" r="48" fill="none" stroke="rgba(0,0,0,0.02)" strokeWidth="1" />
      </svg>
    </div>
  );
}
