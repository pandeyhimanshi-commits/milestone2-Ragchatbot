"use client";

import { useMemo } from "react";
import { GrowwLogoHero } from "./GrowwLogo";

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export function GreetingHeadline() {
  const line = useMemo(() => getGreeting(), []);

  return (
    <div className="mb-6 flex flex-col items-center text-center">
      <div className="mb-4">
        <GrowwLogoHero className="h-20 w-20" />
      </div>
      <h2 className="text-2xl font-semibold text-gray-900 md:text-3xl">
        {line}, Himanshi
      </h2>
      <p className="mt-1.5 max-w-md text-sm text-gray-500 md:text-base">
        How can I help you grow your portfolio today?
      </p>
    </div>
  );
}
