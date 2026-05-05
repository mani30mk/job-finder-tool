"use client";

import { useEffect, useState } from "react";
import {
  Briefcase,
  TrendingUp,
  Star,
  Bookmark,
} from "lucide-react";
import { api } from "@/lib/api";
import { Job, DashboardStats } from "@/lib/types";
import { StatCard } from "../StatCard";
import { JobCard } from "../JobCard";

export function DashboardScreen() {
  const [stats, setStats] = useState<DashboardStats>({
    totalJobsAvailable: 0,
    highMatchCount: 0,
    newJobsLast24h: 0,
    savedJobsCount: 0,
  });
  const [featuredJobs, setFeaturedJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [statsData, jobs] = await Promise.all([
          api.getDashboardStats(),
          api.getRecommendations(6, 0.0),
        ]);
        setStats(statsData);
        setFeaturedJobs(jobs.slice(0, 6));
      } catch (err) {
        console.error("[DashboardScreen] loadData failed:", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-8 border border-blue-100">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Welcome Back!
        </h1>
        <p className="text-gray-600">
          Here&apos;s a summary of your job opportunities this week.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={<Briefcase className="w-6 h-6" />}
          label="Available Jobs"
          value={stats.totalJobsAvailable}
          subtext="Matching your profile"
          colorClass="text-blue-600"
        />
        <StatCard
          icon={<Star className="w-6 h-6" />}
          label="High Match"
          value={stats.highMatchCount}
          subtext="70%+ match score"
          colorClass="text-green-600"
        />
        <StatCard
          icon={<TrendingUp className="w-6 h-6" />}
          label="New Today"
          value={stats.newJobsLast24h}
          subtext="Last 24 hours"
          colorClass="text-amber-600"
        />
        <StatCard
          icon={<Bookmark className="w-6 h-6" />}
          label="Saved Jobs"
          value={stats.savedJobsCount}
          subtext="For later review"
          colorClass="text-purple-600"
        />
      </div>

      {/* Featured Jobs */}
      <div>
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Featured Opportunities
          </h2>
          <p className="text-gray-600">
            Best matches for your profile this week
          </p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse"
              >
                <div className="h-8 bg-gray-200 rounded w-3/4 mb-4" />
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-full" />
                  <div className="h-4 bg-gray-200 rounded w-5/6" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {featuredJobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>

      {/* CTA Section */}
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <h3 className="text-xl font-bold text-gray-900 mb-2">
          Explore More Opportunities
        </h3>
        <p className="text-gray-600 mb-6">
          Browse through all available jobs and find your perfect match
        </p>
        <a
          href="/jobs"
          className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-lg transition"
        >
          View All Jobs
        </a>
      </div>
    </div>
  );
}
