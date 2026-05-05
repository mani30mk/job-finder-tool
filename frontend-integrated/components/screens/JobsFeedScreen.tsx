"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Job } from "@/lib/types";
import { JobCard } from "../JobCard";
import { FilterSidebar, FilterValues } from "../FilterSidebar";

interface JobsFeedScreenProps {
  initialSearchQuery?: string;
}

export function JobsFeedScreen({ initialSearchQuery = "" }: JobsFeedScreenProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterValues>({
    employmentTypes: [],
    locations: [],
    remoteOnly: false,
    minMatchScore: 0,
    salaryMin: 0,
    salaryMax: 500000,
    experienceLevel: "",
  });
  const [searchQuery, setSearchQuery] = useState(initialSearchQuery);

useEffect(() => {
    const loadJobs = async () => {
      setLoading(true);
      setError(null);
      try {
        const fetchedJobs = await api.getRecommendations(100, 0.0);
        setJobs(fetchedJobs);
      } catch (e) {
        setError("Failed to load jobs. Is the backend running?");
      } finally {
        setLoading(false);
      }
    };

    // Only run in browser, never during SSR
    if (typeof window !== "undefined") {
      loadJobs();
    }
  }, []);

  // Client-side filtering — computed from jobs directly (no separate state)
  const filteredJobs = jobs.filter((job) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matches =
        job.title.toLowerCase().includes(q) ||
        job.company.toLowerCase().includes(q) ||
        job.requiredSkills.some((s) => s.toLowerCase().includes(q));
      if (!matches) return false;
    }
    if (filters.employmentTypes.length > 0) {
      if (!filters.employmentTypes.some((t) => t.toLowerCase() === job.employmentType)) return false;
    }
    if (filters.remoteOnly && job.remote !== "remote") return false;
    if (filters.minMatchScore > 0 && job.matchScore < filters.minMatchScore) return false;

    // Location filter
    if (filters.locations.length > 0) {
      const jobLoc = job.location.toLowerCase();
      const matchesLocation = filters.locations.some((loc) => {
        const l = loc.toLowerCase();

        // "India" filter — match all Indian cities + "india" in location
        if (l === "india") {
          const indianCities = [
            "india", "bangalore", "bengaluru", "mumbai", "delhi", "noida",
            "gurgaon", "gurugram", "hyderabad", "chennai", "pune", "kolkata",
            "ahmedabad", "jaipur", "lucknow", "kochi", "cochin", "chandigarh",
            "indore", "coimbatore", "thiruvananthapuram", "nagpur", "surat",
            "visakhapatnam", "bhopal", "patna", "vadodara", "navi mumbai",
            "kanchipuram", "mysore", "mangalore", "goa", "dehradun",
            "salem", "madurai", "trichy", "thanjavur",
          ];
          return indianCities.some((city) => jobLoc.includes(city))
            || job.source_platform === "internshala";
        }

        // Handle "Delhi / NCR" matching "delhi", "noida", "gurgaon"
        if (l === "delhi / ncr") {
          return jobLoc.includes("delhi") || jobLoc.includes("noida") || jobLoc.includes("gurgaon") || jobLoc.includes("gurugram");
        }
        return jobLoc.includes(l);
      });
      if (!matchesLocation) return false;
    }

    // Experience level filter
    if (filters.experienceLevel) {
      const titleLower = job.title.toLowerCase();
      if (filters.experienceLevel === "intern") {
        if (!titleLower.match(/intern|entry|trainee|fresher|graduate/)) return false;
      } else if (filters.experienceLevel === "junior") {
        if (!titleLower.match(/junior|jr|associate|entry|intern|i\b|1\b/)) return false;
      } else if (filters.experienceLevel === "mid") {
        // Mid = not explicitly senior or intern
        if (titleLower.match(/senior|lead|principal|staff|intern|entry|junior|jr/)) return false;
      } else if (filters.experienceLevel === "senior") {
        if (!titleLower.match(/senior|sr|lead|principal|staff|architect|manager|director/)) return false;
      }
    }

    return true;
  });

  return (
    <div className="flex gap-6">
      <FilterSidebar onFilterChange={setFilters} />

      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Job Opportunities</h1>
          <p className="text-gray-600">
            {loading
              ? "Loading jobs..."
              : `${filteredJobs.length} jobs available${filters.employmentTypes.length > 0 ? " with your filters" : ""}`}
          </p>
        </div>

        {/* Search */}
        <div className="mb-4">
          <input
            type="text"
            placeholder="Search by title, company, or skill..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none"
          />
        </div>

        {/* States */}
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
                <div className="flex items-start space-x-4">
                  <div className="w-12 h-12 bg-gray-200 rounded-lg flex-shrink-0" />
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
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
            <p className="text-red-600 font-semibold mb-2">⚠️ {error}</p>
            <p className="text-sm text-red-500">
              Make sure uvicorn is running: <code className="bg-red-100 px-1 rounded">uvicorn api.main:app --reload --port 8000</code>
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        ) : filteredJobs.length > 0 ? (
          <div className="space-y-4">
            {filteredJobs.map((job) => (
              <JobCard key={job.id} job={job} isSaved={api.isJobSaved(job.id)} />
            ))}
          </div>
        ) : jobs.length > 0 ? (
          // Jobs loaded but filters removed everything
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <p className="text-lg text-gray-600 mb-2">No jobs match your filters</p>
            <p className="text-gray-500">Try relaxing the filters or clearing search</p>
            <button
              onClick={() => { setSearchQuery(""); setFilters({ employmentTypes: [], locations: [], remoteOnly: false, minMatchScore: 0, salaryMin: 0, salaryMax: 500000, experienceLevel: "" }); }}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700"
            >
              Clear Filters
            </button>
          </div>
        ) : (
          // Loaded but truly 0 jobs from backend
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <p className="text-lg text-gray-600 mb-2">No jobs in database</p>
            <p className="text-gray-500 mb-4">Run the scraper to populate jobs</p>
            <code className="block bg-gray-100 rounded px-4 py-2 text-sm text-left">
              python run_scrapers.py
            </code>
          </div>
        )}
      </div>
    </div>
  );
}