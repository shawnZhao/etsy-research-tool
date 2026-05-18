"use client";

import React, { type ReactNode } from "react";

interface TooltipProps {
  content: string;
  children: ReactNode;
  position?: "top" | "bottom";
}

export function Tooltip({ content, children, position = "top" }: TooltipProps) {
  const positionClasses =
    position === "bottom"
      ? "top-full mt-2"
      : "bottom-full mb-2";

  return (
    <span className="group relative inline-flex items-center">
      {children}
      <span
        className={`absolute left-1/2 -translate-x-1/2 ${positionClasses} px-3 py-2 bg-gray-800 text-white text-xs rounded shadow-lg w-64 max-w-[90vw] text-center z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible focus-within:opacity-100 focus-within:visible transition-opacity duration-150 pointer-events-none`}
      >
        {content}
      </span>
    </span>
  );
}
