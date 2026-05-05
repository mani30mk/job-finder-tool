export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  salary?: {
    min: number;
    max: number;
    currency: string;
  };
  matchScore: number;
  description: string;
  requiredSkills: string[];
  benefits: string[];
  employmentType: "full-time" | "part-time" | "contract" | "internship";
  remote: "remote" | "hybrid" | "on-site";
  postedAt: string;
  link: string;
  companyLogo?: string;
  isNew: boolean;
  source_platform?: string;
}

export interface DashboardStats {
  totalJobsAvailable: number;
  highMatchCount: number;
  newJobsLast24h: number;
  savedJobsCount: number;
}

export interface UserProfile {
  name: string;
  title: string;
  skills: string[];
  experience: string;
  location: string;
  email?: string;
  apiUrl?: string;
  notificationsEnabled: boolean;
}

export interface FilterOptions {
  employmentTypes: string[];
  locations: string[];
  salaryRange: [number, number];
  remoteOnly: boolean;
  minMatchScore: number;
}
