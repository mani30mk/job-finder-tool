"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, Bell, Settings, LogOut, X, Briefcase, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface Notification {
  id: string;
  title: string;
  message: string;
  time: string;
  read: boolean;
  type: "job" | "system" | "match";
}

function getNotifications(): Notification[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem("notifications");
    if (stored) return JSON.parse(stored);
  } catch {}
  // Default notifications
  const defaults: Notification[] = [
    {
      id: "1",
      title: "New Job Matches",
      message: "12 new jobs match your profile today",
      time: new Date().toISOString(),
      read: false,
      type: "match",
    },
    {
      id: "2",
      title: "Profile Tip",
      message: "Upload your resume for better job matching",
      time: new Date(Date.now() - 3600000).toISOString(),
      read: false,
      type: "system",
    },
    {
      id: "3",
      title: "Saved Job Update",
      message: "A saved job posting was recently updated",
      time: new Date(Date.now() - 7200000).toISOString(),
      read: true,
      type: "job",
    },
  ];
  localStorage.setItem("notifications", JSON.stringify(defaults));
  return defaults;
}

function markAllRead() {
  if (typeof window === "undefined") return;
  try {
    const stored = localStorage.getItem("notifications");
    if (stored) {
      const notifs: Notification[] = JSON.parse(stored);
      notifs.forEach((n) => (n.read = true));
      localStorage.setItem("notifications", JSON.stringify(notifs));
    }
  } catch {}
}

function markOneRead(id: string) {
  if (typeof window === "undefined") return;
  try {
    const stored = localStorage.getItem("notifications");
    if (stored) {
      const notifs: Notification[] = JSON.parse(stored);
      const n = notifs.find((n) => n.id === id);
      if (n) n.read = true;
      localStorage.setItem("notifications", JSON.stringify(notifs));
    }
  } catch {}
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

interface HeaderProps {
  onSearch?: (query: string) => void;
  activeTab?: string;
}

export function Header({ onSearch, activeTab }: HeaderProps) {
  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const notifRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setNotifications(getNotifications());
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    onSearch?.(query);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Navigate to jobs page with search query
      router.push(`/jobs?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchOpen(false);
    }
  };

  const handleMarkAllRead = () => {
    markAllRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const handleNotifClick = (notif: Notification) => {
    markOneRead(notif.id);
    setNotifications((prev) =>
      prev.map((n) => (n.id === notif.id ? { ...n, read: true } : n))
    );
    if (notif.type === "match" || notif.type === "job") {
      setNotifOpen(false);
      router.push("/jobs");
    }
  };

  const notifIcon = (type: Notification["type"]) => {
    switch (type) {
      case "job":
        return <Briefcase className="w-4 h-4 text-blue-500" />;
      case "match":
        return <Briefcase className="w-4 h-4 text-green-500" />;
      case "system":
        return <Bell className="w-4 h-4 text-amber-500" />;
    }
  };

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-sm safe-area-inset-left safe-area-inset-right">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-16 md:h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">JH</span>
            </div>
            <span className="font-bold text-gray-900 hidden sm:inline">
              JobHunter
            </span>
          </Link>

          {/* Search Bar - Desktop */}
          <form onSubmit={handleSearchSubmit} className="hidden md:flex flex-1 max-w-md mx-8">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search jobs..."
                value={searchQuery}
                onChange={handleSearch}
                className="w-full pl-10 pr-4 py-2 rounded-lg bg-gray-100 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              />
            </div>
          </form>

          {/* Right Actions */}
          <div className="flex items-center space-x-1 sm:space-x-4">
            {/* Mobile Search */}
            <button
              onClick={() => setSearchOpen(!searchOpen)}
              className="md:hidden p-2.5 hover:bg-gray-100 rounded-lg transition active:bg-gray-200 touch-target"
              aria-label="Search jobs"
            >
              <Search className="w-6 h-6 text-gray-600" />
            </button>

            {/* Notifications */}
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => {
                  setNotifOpen(!notifOpen);
                  setMenuOpen(false);
                }}
                className="relative p-2.5 hover:bg-gray-100 rounded-lg transition active:bg-gray-200 touch-target"
                aria-label="Notifications"
                id="notification-bell"
              >
                <Bell className="w-6 h-6 text-gray-600" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 min-w-[18px] h-[18px] flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full px-1 animate-pulse">
                    {unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Dropdown */}
              {notifOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-2xl border border-gray-200 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
                    <h3 className="font-semibold text-gray-900 text-sm">Notifications</h3>
                    {unreadCount > 0 && (
                      <button
                        onClick={handleMarkAllRead}
                        className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>
                  <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
                    {notifications.length === 0 ? (
                      <div className="px-4 py-8 text-center text-gray-500 text-sm">
                        No notifications yet
                      </div>
                    ) : (
                      notifications.map((notif) => (
                        <button
                          key={notif.id}
                          onClick={() => handleNotifClick(notif)}
                          className={cn(
                            "w-full text-left px-4 py-3 hover:bg-gray-50 transition flex gap-3 items-start",
                            !notif.read && "bg-blue-50/50"
                          )}
                        >
                          <div className="mt-0.5 flex-shrink-0">
                            {notifIcon(notif.type)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className={cn(
                                "text-sm truncate",
                                notif.read ? "text-gray-700" : "text-gray-900 font-semibold"
                              )}>
                                {notif.title}
                              </p>
                              {!notif.read && (
                                <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                              )}
                            </div>
                            <p className="text-xs text-gray-500 mt-0.5 truncate">{notif.message}</p>
                            <p className="text-[10px] text-gray-400 mt-1 flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {timeAgo(notif.time)}
                            </p>
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                  <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
                    <Link
                      href="/profile"
                      className="text-xs text-gray-500 hover:text-gray-700 font-medium"
                      onClick={() => setNotifOpen(false)}
                    >
                      Manage notification settings →
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {/* Profile Menu */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => {
                  setMenuOpen(!menuOpen);
                  setNotifOpen(false);
                }}
                className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold hover:bg-blue-200 transition active:bg-blue-300 touch-target"
                aria-label="Profile menu"
              >
                U
              </button>

              {menuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                  <Link
                    href="/profile"
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    onClick={() => setMenuOpen(false)}
                  >
                    <Settings className="w-4 h-4 inline mr-2" />
                    Profile & Settings
                  </Link>
                  <button className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100">
                    <LogOut className="w-4 h-4 inline mr-2" />
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Mobile Search - Expanded */}
        {searchOpen && (
          <div className="pb-4 md:hidden">
            <form onSubmit={handleSearchSubmit} className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search jobs..."
                value={searchQuery}
                onChange={handleSearch}
                className="w-full pl-10 pr-10 py-2 rounded-lg bg-gray-100 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                autoFocus
              />
              <button
                type="button"
                onClick={() => { setSearchOpen(false); setSearchQuery(""); }}
                className="absolute right-3 top-1/2 -translate-y-1/2"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </form>
          </div>
        )}
      </div>
    </header>
  );
}
