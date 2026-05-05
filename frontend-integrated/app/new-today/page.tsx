"use client";

import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import { Header } from "@/components/Header";
import { Navigation } from "@/components/Navigation";
import { JobCard } from "@/components/JobCard";
import { api } from "@/lib/api";
import { Job } from "@/lib/types";

export default function NewTodayPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadNewJobs = async () => {
      setLoading(true);
      // Try last 24 hours first
      let newJobs = await api.getNewJobs(24, 50);
      // If no recent jobs, expand to last 7 days
      if (newJobs.length === 0) {
        newJobs = await api.getNewJobs(168, 50);
      }
      setJobs(newJobs);
      setLoading(false);
    };

    loadNewJobs();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1 pb-24 lg:pb-0">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center space-x-3">
              <Star className="w-8 h-8 text-amber-500" />
              <span>New Today</span>
            </h1>
            <p className="text-gray-600">
              Jobs posted in the last 24 hours, fresh opportunities
            </p>
          </div>

          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse"
                >
                  <div className="flex items-start space-x-4">
                    <div className="w-12 h-12 bg-gray-200 rounded-lg" />
                    <div className="flex-1">
                      <div className="h-6 bg-gray-200 rounded w-2/3 mb-2" />
                      <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
                      <div className="space-y-2">
                        <div className="h-4 bg-gray-200 rounded w-full" />
                        <div className="h-4 bg-gray-200 rounded w-5/6" />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : jobs.length > 0 ? (
            <div className="space-y-4">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  isSaved={api.isJobSaved(job.id)}
                />
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
              <Star className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No New Jobs Today
              </h3>
              <p className="text-gray-500">
                Check back later for fresh opportunities
              </p>
            </div>
          )}
        </div>
      </main>
      <Navigation />
    </div>
  );
}
