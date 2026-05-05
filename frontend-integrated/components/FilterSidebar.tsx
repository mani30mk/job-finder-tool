"use client";

import { useState } from "react";
import { ChevronDown, Sliders } from "lucide-react";
import { cn } from "@/lib/utils";

interface FilterSidebarProps {
  onFilterChange?: (filters: FilterValues) => void;
  className?: string;
}

export interface FilterValues {
  employmentTypes: string[];
  locations: string[];
  remoteOnly: boolean;
  minMatchScore: number;
  salaryMin: number;
  salaryMax: number;
  experienceLevel: string;
}

export function FilterSidebar({ onFilterChange, className }: FilterSidebarProps) {
  const [expandedSections, setExpandedSections] = useState<
    Record<string, boolean>
  >({
    employment: true,
    location: true,
    remote: true,
    experience: false,
    salary: false,
    matchScore: true,
  });

  const [filters, setFilters] = useState<FilterValues>({
    employmentTypes: [],
    locations: [],
    remoteOnly: false,
    minMatchScore: 0,
    salaryMin: 0,
    salaryMax: 500000,
    experienceLevel: "",
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleEmploymentTypeChange = (type: string) => {
    const newTypes = filters.employmentTypes.includes(type)
      ? filters.employmentTypes.filter((t) => t !== type)
      : [...filters.employmentTypes, type];

    const updatedFilters = { ...filters, employmentTypes: newTypes };
    setFilters(updatedFilters);
    onFilterChange?.(updatedFilters);
  };

  const handleLocationChange = (loc: string) => {
    const newLocs = filters.locations.includes(loc)
      ? filters.locations.filter((l) => l !== loc)
      : [...filters.locations, loc];

    const updatedFilters = { ...filters, locations: newLocs };
    setFilters(updatedFilters);
    onFilterChange?.(updatedFilters);
  };

  const handleRemoteChange = () => {
    const updatedFilters = { ...filters, remoteOnly: !filters.remoteOnly };
    setFilters(updatedFilters);
    onFilterChange?.(updatedFilters);
  };

  const handleScoreChange = (value: number) => {
    const updatedFilters = { ...filters, minMatchScore: value };
    setFilters(updatedFilters);
    onFilterChange?.(updatedFilters);
  };

  const handleExperienceChange = (level: string) => {
    const updatedFilters = {
      ...filters,
      experienceLevel: filters.experienceLevel === level ? "" : level,
    };
    setFilters(updatedFilters);
    onFilterChange?.(updatedFilters);
  };

  const employmentTypes = [
    "Full-time",
    "Part-time",
    "Contract",
    "Internship",
    "Freelance",
  ];

  const locationOptions = [
    "India",
    "Bangalore",
    "Chennai",
    "Hyderabad",
    "Pune",
    "Mumbai",
    "Delhi / NCR",
    "Remote",
  ];

  const experienceLevels = [
    { label: "Intern / Entry", value: "intern" },
    { label: "Junior (0-2 yrs)", value: "junior" },
    { label: "Mid (2-5 yrs)", value: "mid" },
    { label: "Senior (5+ yrs)", value: "senior" },
  ];

  const activeFilterCount = [
    filters.employmentTypes.length > 0,
    filters.locations.length > 0,
    filters.remoteOnly,
    filters.minMatchScore > 0,
    filters.experienceLevel !== "",
  ].filter(Boolean).length;

  return (
    <aside
      className={cn(
        "hidden lg:block w-64 bg-white rounded-lg border border-gray-200 p-6 h-fit sticky top-20",
        className
      )}
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Sliders className="w-5 h-5 text-gray-600" />
          <h2 className="font-bold text-gray-900 text-lg">Filters</h2>
        </div>
        {activeFilterCount > 0 && (
          <span className="text-xs font-semibold px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
            {activeFilterCount}
          </span>
        )}
      </div>

      {/* Employment Type */}
      <div className="mb-5">
        <button
          onClick={() => toggleSection("employment")}
          className="w-full flex items-center justify-between py-2 hover:bg-gray-50 rounded px-2 transition"
        >
          <span className="font-semibold text-gray-900 text-sm">
            Employment Type
          </span>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-gray-500 transition-transform",
              expandedSections.employment && "rotate-180"
            )}
          />
        </button>

        {expandedSections.employment && (
          <div className="space-y-1 mt-2 ml-1">
            {employmentTypes.map((type) => (
              <label key={type} className="flex items-center gap-3 cursor-pointer p-1.5 rounded hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={filters.employmentTypes.includes(type)}
                  onChange={() => handleEmploymentTypeChange(type)}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 cursor-pointer"
                />
                <span className="text-sm text-gray-700">{type}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-gray-100 my-3" />

      {/* Location */}
      <div className="mb-5">
        <button
          onClick={() => toggleSection("location")}
          className="w-full flex items-center justify-between py-2 hover:bg-gray-50 rounded px-2 transition"
        >
          <span className="font-semibold text-gray-900 text-sm">Location</span>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-gray-500 transition-transform",
              expandedSections.location && "rotate-180"
            )}
          />
        </button>

        {expandedSections.location && (
          <div className="space-y-1 mt-2 ml-1">
            {locationOptions.map((loc) => (
              <label key={loc} className="flex items-center gap-3 cursor-pointer p-1.5 rounded hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={filters.locations.includes(loc)}
                  onChange={() => handleLocationChange(loc)}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 cursor-pointer"
                />
                <span className="text-sm text-gray-700">{loc}</span>
              </label>
            ))}
            {/* Remote Only toggle inside location */}
            <label className="flex items-center gap-3 cursor-pointer p-1.5 rounded hover:bg-gray-50 mt-1 border-t border-gray-100 pt-2">
              <input
                type="checkbox"
                checked={filters.remoteOnly}
                onChange={handleRemoteChange}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 cursor-pointer"
              />
              <span className="text-sm text-gray-700 font-medium">Remote Only</span>
            </label>
          </div>
        )}
      </div>

      <div className="border-t border-gray-100 my-3" />

      {/* Experience Level */}
      <div className="mb-5">
        <button
          onClick={() => toggleSection("experience")}
          className="w-full flex items-center justify-between py-2 hover:bg-gray-50 rounded px-2 transition"
        >
          <span className="font-semibold text-gray-900 text-sm">Experience Level</span>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-gray-500 transition-transform",
              expandedSections.experience && "rotate-180"
            )}
          />
        </button>

        {expandedSections.experience && (
          <div className="space-y-1 mt-2 ml-1">
            {experienceLevels.map((level) => (
              <label key={level.value} className="flex items-center gap-3 cursor-pointer p-1.5 rounded hover:bg-gray-50">
                <input
                  type="radio"
                  name="experienceLevel"
                  checked={filters.experienceLevel === level.value}
                  onChange={() => handleExperienceChange(level.value)}
                  className="w-4 h-4 border-gray-300 text-blue-600 cursor-pointer"
                />
                <span className="text-sm text-gray-700">{level.label}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-gray-100 my-3" />

      {/* Match Score Filter */}
      <div className="mb-5">
        <button
          onClick={() => toggleSection("matchScore")}
          className="w-full flex items-center justify-between py-2 hover:bg-gray-50 rounded px-2 transition"
        >
          <span className="font-semibold text-gray-900 text-sm">
            Min Match Score
          </span>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-gray-500 transition-transform",
              expandedSections.matchScore && "rotate-180"
            )}
          />
        </button>

        {expandedSections.matchScore && (
          <div className="mt-3 ml-2 space-y-2">
            <input
              type="range"
              min="0"
              max="100"
              value={Math.round(filters.minMatchScore * 100)}
              onChange={(e) => handleScoreChange(Number(e.target.value) / 100)}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="text-sm text-gray-600 font-medium">
              {Math.round(filters.minMatchScore * 100)}% and above
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-gray-100 my-3" />

      {/* Clear Filters */}
      <button
        onClick={() => {
          const clearedFilters: FilterValues = {
            employmentTypes: [],
            locations: [],
            remoteOnly: false,
            minMatchScore: 0,
            salaryMin: 0,
            salaryMax: 500000,
            experienceLevel: "",
          };
          setFilters(clearedFilters);
          onFilterChange?.(clearedFilters);
        }}
        className="w-full py-2.5 px-3 bg-gray-100 hover:bg-gray-200 text-gray-900 font-semibold text-sm rounded-lg transition"
      >
        Clear All Filters
      </button>
    </aside>
  );
}
