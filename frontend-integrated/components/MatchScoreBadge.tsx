"use client";

import { cn } from "@/lib/utils";

interface MatchScoreBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function MatchScoreBadge({
  score,
  size = "md",
  className,
}: MatchScoreBadgeProps) {
  const percentage = Math.round(score * 100);
  let bgColor = "bg-red-50 text-red-700";
  let borderColor = "border-red-200";

  if (percentage >= 70) {
    bgColor = "bg-green-50 text-green-700";
    borderColor = "border-green-200";
  } else if (percentage >= 40) {
    bgColor = "bg-amber-50 text-amber-700";
    borderColor = "border-amber-200";
  }

  const sizeClasses = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm font-semibold",
    lg: "px-4 py-2 text-base font-bold",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-lg border font-semibold",
        sizeClasses[size],
        bgColor,
        borderColor,
        className
      )}
    >
      <span className="mr-1">◆</span>
      {percentage}%
    </div>
  );
}
