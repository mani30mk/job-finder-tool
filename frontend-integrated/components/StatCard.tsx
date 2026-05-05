"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  icon: ReactNode;
  label: string;
  value: number | string;
  subtext?: string;
  className?: string;
  colorClass?: string;
}

export function StatCard({
  icon,
  label,
  value,
  subtext,
  className,
  colorClass = "text-blue-600",
}: StatCardProps) {
  return (
    <div
      className={cn(
        "bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow",
        className
      )}
    >
      <div className={cn("w-12 h-12 rounded-lg flex items-center justify-center mb-4", colorClass + " bg-opacity-10")}>
        <div className={colorClass}>{icon}</div>
      </div>
      <p className="text-sm text-gray-600 font-medium mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-900 mb-1">{value}</p>
      {subtext && <p className="text-xs text-gray-500">{subtext}</p>}
    </div>
  );
}
