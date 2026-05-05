"use client";

import { useState } from "react";
import { Heart, MapPin, Briefcase, DollarSign, ExternalLink } from "lucide-react";
import { Job } from "@/lib/types";
import { MatchScoreBadge } from "./MatchScoreBadge";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

interface JobCardProps {
  job: Job;
  onSave?: (job: Job) => void;
  isSaved?: boolean;
  onApply?: (job: Job) => void;
  className?: string;
}

export function JobCard({
  job,
  onSave,
  isSaved: initialSaved = false,
  onApply,
  className,
}: JobCardProps) {
  const [isSaved, setIsSaved] = useState(initialSaved);
  const [isHovered, setIsHovered] = useState(false);

  const handleSave = () => {
    api.toggleSaveJob(job);
    setIsSaved(!isSaved);
    onSave?.(job);
  };

  const handleApply = () => {
    window.open(job.link, "_blank");
    onApply?.(job);
  };

  return (
    <div
      className={cn(
        "bg-white rounded-lg border border-gray-200 p-4 sm:p-6 hover:shadow-md hover:border-gray-300 transition-all duration-200",
        isHovered && "shadow-md border-gray-300",
        className
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Header with Company and Match Score */}
      <div className="flex items-start justify-between gap-3 sm:gap-4 mb-4">
        <div className="flex items-start gap-3 sm:gap-4 flex-1">
          {/* Company Logo */}
          {job.companyLogo ? (
            <img
              src={job.companyLogo}
              alt={job.company}
              className="w-12 h-12 sm:w-14 sm:h-14 rounded-lg object-cover bg-gray-100 flex-shrink-0"
            />
          ) : (
            <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-lg bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-sm sm:text-base">
                {job.company[0].toUpperCase()}
              </span>
            </div>
          )}

          <div className="flex-1 min-w-0">
            {job.isNew && (
              <div className="inline-block mb-2 px-2 py-1 bg-blue-100 text-blue-700 text-xs font-semibold rounded">
                New
              </div>
            )}
            <h3 className="text-base sm:text-lg font-bold text-gray-900 break-words">
              {job.title}
            </h3>
            <p className="text-xs sm:text-sm text-gray-600">{job.company}</p>
          </div>
        </div>

        {/* Save Button */}
        <button
          onClick={handleSave}
          className="flex-shrink-0 ml-2 p-2.5 sm:p-2 rounded-lg hover:bg-gray-100 transition active:bg-gray-200 touch-target"
          aria-label={isSaved ? "Remove from saved" : "Save job"}
        >
          <Heart
            className={cn(
              "w-6 h-6 sm:w-5 sm:h-5 transition-colors",
              isSaved ? "fill-red-500 text-red-500" : "text-gray-400"
            )}
          />
        </button>
      </div>

      {/* Match Score */}
      <div className="mb-4">
        <MatchScoreBadge score={job.matchScore} size="md" />
      </div>

      {/* Job Details */}
      <div className="space-y-2 mb-4 text-xs sm:text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 flex-shrink-0" />
          <span className="line-clamp-1">{job.location}</span>
          <span className="text-gray-400 mx-1">•</span>
          <span className="capitalize">{job.remote}</span>
        </div>

        <div className="flex items-center gap-2">
          <Briefcase className="w-4 h-4 flex-shrink-0" />
          <span className="capitalize">{job.employmentType}</span>
        </div>

        {job.salary && (
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 flex-shrink-0" />
            <span className="line-clamp-1">
              {job.salary.currency}{" "}
              {Math.round(job.salary.min / 1000)}K -{" "}
              {Math.round(job.salary.max / 1000)}K
            </span>
          </div>
        )}
      </div>

      {/* Skills */}
      {job.requiredSkills.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-gray-500 uppercase font-semibold mb-2">
            Key Skills
          </p>
          <div className="flex flex-wrap gap-2">
            {job.requiredSkills.slice(0, 3).map((skill) => (
              <span
                key={skill}
                className="px-2.5 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-full"
              >
                {skill}
              </span>
            ))}
            {job.requiredSkills.length > 3 && (
              <span className="px-2.5 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-full">
                +{job.requiredSkills.length - 3}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Description Preview */}
      <p className="text-sm text-gray-700 mb-4 line-clamp-2">
        {job.description}
      </p>

      {/* Apply Button */}
      <button
        onClick={handleApply}
        className="w-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold py-3 sm:py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 touch-target text-sm sm:text-base"
      >
        <span>View & Apply</span>
        <ExternalLink className="w-4 h-4 sm:w-4 sm:h-4" />
      </button>
    </div>
  );
}
