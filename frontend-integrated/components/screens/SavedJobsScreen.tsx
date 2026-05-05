"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Job } from "@/lib/types";
import { JobCard } from "../JobCard";
import { Bookmark } from "lucide-react";

export function SavedJobsScreen() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSavedJobs = () => {
      setLoading(true);
      const saved = api.getSavedJobs();
      setJobs(saved);
      setLoading(false);
    };

    loadSavedJobs();
  }, []);

  const handleRemove = (jobId: string) => {
    setJobs((prev) => prev.filter((job) => job.id !== jobId));
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center space-x-3">
          <Bookmark className="w-8 h-8 text-blue-600" />
          <span>Saved Jobs</span>
        </h1>
        <p className="text-gray-600">
          {jobs.length} job{jobs.length !== 1 ? "s" : ""} saved for later
        </p>
      </div>

      {/* Jobs Grid */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
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
            <div key={job.id}>
              <JobCard
                job={job}
                isSaved={true}
                onSave={() => handleRemove(job.id)}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <Bookmark className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Saved Jobs Yet
          </h3>
          <p className="text-gray-500 mb-6">
            Start saving jobs you&apos;re interested in to view them later
          </p>
          <a
            href="/jobs"
            className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg transition"
          >
            Browse Jobs
          </a>
        </div>
      )}
    </div>
  );
}
