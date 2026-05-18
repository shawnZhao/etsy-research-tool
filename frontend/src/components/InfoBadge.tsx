"use client";

import React from "react";
import { Tooltip } from "./Tooltip";

interface InfoBadgeProps {
  label: string;
  tooltip?: string | null;
}

export function InfoBadge({ label, tooltip }: InfoBadgeProps) {
  if (!tooltip) {
    return <span>{label}</span>;
  }

  return (
    <span className="inline-flex items-center gap-1">
      <span>{label}</span>
      <Tooltip content={tooltip}>
        <span
          className="inline-flex items-center justify-center w-4 h-4 text-xs bg-gray-200 text-gray-600 rounded-full cursor-help leading-none"
          aria-label="More info"
        >
          ?
        </span>
      </Tooltip>
    </span>
  );
}
