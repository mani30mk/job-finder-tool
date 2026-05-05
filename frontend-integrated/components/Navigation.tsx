"use client";

import { LayoutDashboard, Briefcase, Star, Bookmark, User } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/new-today", label: "New Today", icon: Star },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/profile", label: "Profile", icon: User },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 lg:static lg:border-t-0 lg:border-b z-50 safe-area-inset-left safe-area-inset-right safe-area-inset-bottom">
      <div className="max-w-7xl mx-auto px-0 sm:px-6 lg:px-8">
        <div className="flex items-center justify-around lg:justify-start lg:space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col lg:flex-row lg:items-center lg:space-x-2 flex-1 lg:flex-none px-2 sm:px-3 py-3 sm:py-4 lg:px-4 lg:py-3 text-center lg:text-left rounded-t-lg lg:rounded-b-lg text-xs sm:text-sm font-medium transition-colors active:bg-blue-100 lg:active:bg-transparent touch-target",
                  isActive
                    ? "text-blue-600 bg-blue-50 lg:bg-transparent lg:border-b-2 lg:border-blue-600"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50 lg:hover:bg-transparent"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon className="w-6 h-6 mx-auto lg:mx-0 mb-1 lg:mb-0 sm:w-5 sm:h-5" />
                <span className="text-xs lg:text-sm">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
