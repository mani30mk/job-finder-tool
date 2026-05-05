/**
 * api.ts — Job Hunter API client
 */
import { Job, DashboardStats } from "./types";
import { MOCK_JOBS } from "./mock-data";

function getBaseUrl(): string {
  if (typeof window === "undefined")
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return (
    localStorage.getItem("apiUrl") ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000"
  );
}

// ── Backend shapes ────────────────────────────────────────────────────────────
interface BackendJob {
  job_id?: string;
  id?: string;
  title: string;
  company: string;
  location?: string;
  employment_type?: string;
  description?: string;
  requirements?: string;
  apply_url?: string;
  url?: string;
  source_platform?: string;
  posted_date?: string;
  scraped_at?: string;
  is_active?: boolean;
  is_new?: boolean;
  salary?: string | null;
  match_score?: number;
  match_reasons?: string[];
}

// ── Transformer ───────────────────────────────────────────────────────────────
function transformJob(b: BackendJob, index: number): Job {
  const loc = b.location || "";
  const type = b.employment_type || "";
  const combined = (loc + " " + type).toLowerCase();

  const remote: "remote" | "hybrid" | "on-site" = combined.includes("remote")
    ? "remote"
    : combined.includes("hybrid")
    ? "hybrid"
    : "on-site";

  const employmentType: "full-time" | "part-time" | "contract" | "internship" =
    type.toLowerCase().includes("intern")
      ? "internship"
      : type.toLowerCase().includes("part")
      ? "part-time"
      : type.toLowerCase().includes("contract") || type.toLowerCase().includes("freelance")
      ? "contract"
      : "full-time";

  const requiredSkills: string[] =
    b.match_reasons && b.match_reasons.length > 0
      ? b.match_reasons
      : (b.requirements || "")
          .split(/[,;\n]/)
          .map((s) => s.trim())
          .filter(Boolean)
          .slice(0, 6);

  return {
    id: b.job_id || b.id || String(index),
    title: b.title || "Untitled",
    company: b.company || "Unknown",
    location: loc || "Not specified",
    matchScore: typeof b.match_score === "number" ? b.match_score : 0,
    description: b.description || "",
    requiredSkills,
    benefits: [],
    employmentType,
    remote,
    postedAt: b.posted_date || b.scraped_at || new Date().toISOString(),
    link: b.apply_url || b.url || "#",
    companyLogo: `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(b.company || "JH")}`,
    isNew: Boolean(b.is_new),
    source_platform: b.source_platform || "",
  };
}

// ── Timeout helper ────────────────────────────────────────────────────────────
function timedFetch(url: string, timeoutMs = 30000): Promise<Response> {
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs) });
}

// ── API client ────────────────────────────────────────────────────────────────
export const api = {
  get baseUrl() { return getBaseUrl(); },

  async testConnection(): Promise<number | null> {
    try {
      const start = Date.now();
      const res = await fetch(`${this.baseUrl}/`, { signal: AbortSignal.timeout(5000) });
      return res.ok ? Date.now() - start : null;
    } catch { return null; }
  },

  async getRecommendations(limit = 50, minScore = 0.0): Promise<Job[]> {
    const url = `${this.baseUrl}/api/v1/recommendations/default?limit=${limit}&min_score=${minScore}`;
    console.log("[api] fetching:", url);

    try {
      const res = await timedFetch(url);
      console.log("[api] status:", res.status);

      if (!res.ok) {
        console.error("[api] HTTP error:", res.status, res.statusText);
        // If 404, the endpoint doesn't exist on the server yet
        if (res.status === 404) {
          console.warn("[api] /recommendations/default not found — did you update main.py?");
        }
        return MOCK_JOBS;
      }

      const data = await res.json();
      console.log("[api] raw response keys:", Object.keys(data));

      // Handle both shapes: { recommendations: [] } or direct array
      const raw: BackendJob[] = Array.isArray(data)
        ? data
        : Array.isArray(data.recommendations)
        ? data.recommendations
        : [];

      console.log("[api] job count from backend:", raw.length);

      if (raw.length === 0) {
        console.warn("[api] backend returned 0 jobs — check DB has data and min_score");
        return MOCK_JOBS;
      }

      return raw.map((j, i) => transformJob(j, i));
    } catch (err) {
      console.error("[api] fetch failed:", err);
      return MOCK_JOBS;
    }
  },

  async getNewJobs(sinceHours = 24, limit = 30): Promise<Job[]> {
    const url = `${this.baseUrl}/api/v1/jobs/new?since_hours=${sinceHours}&limit=${limit}`;
    console.log("[api] fetching new jobs:", url);

    try {
      const res = await timedFetch(url);
      if (!res.ok) return MOCK_JOBS.filter((j) => j.isNew);

      const data = await res.json();
      const raw: BackendJob[] = Array.isArray(data) ? data : data.jobs ?? [];
      return raw.map((j, i) => transformJob(j, i));
    } catch (err) {
      console.error("[api] getNewJobs failed:", err);
      return MOCK_JOBS.filter((j) => j.isNew);
    }
  },

  async getDashboardStats(): Promise<DashboardStats> {
    try {
      const res = await timedFetch(`${this.baseUrl}/api/v1/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const active = data.active_jobs ?? data.active ?? 0;
      const total = data.total_jobs ?? data.total ?? 0;
      const newCount = data.new_jobs ?? data.new ?? 0;
      return {
        totalJobsAvailable: active || total,
        highMatchCount: 0,
        newJobsLast24h: newCount,
        savedJobsCount: this.getSavedJobs().length,
      };
    } catch {
      // Derive from recommendations
      try {
        const [recs, newJobs] = await Promise.all([
          this.getRecommendations(200, 0),
          this.getNewJobs(),
        ]);
        return {
          totalJobsAvailable: recs.length,
          highMatchCount: recs.filter((j) => j.matchScore >= 0.7).length,
          newJobsLast24h: newJobs.length,
          savedJobsCount: this.getSavedJobs().length,
        };
      } catch {
        return { totalJobsAvailable: 0, highMatchCount: 0, newJobsLast24h: 0, savedJobsCount: 0 };
      }
    }
  },

  // ── Local storage ──────────────────────────────────────────────────────────
  getSavedJobs(): Job[] {
    if (typeof window === "undefined") return [];
    try { const r = localStorage.getItem("savedJobs"); return r ? JSON.parse(r) : []; }
    catch { return []; }
  },
  toggleSaveJob(job: Job): boolean {
    if (typeof window === "undefined") return false;
    const saved = this.getSavedJobs();
    const idx = saved.findIndex((j) => j.id === job.id);
    if (idx >= 0) { saved.splice(idx, 1); localStorage.setItem("savedJobs", JSON.stringify(saved)); return false; }
    saved.unshift(job); localStorage.setItem("savedJobs", JSON.stringify(saved)); return true;
  },
  isJobSaved(jobId: string): boolean {
    if (typeof window === "undefined") return false;
    return this.getSavedJobs().some((j) => j.id === jobId);
  },
  removeSavedJob(jobId: string): void {
    if (typeof window === "undefined") return;
    localStorage.setItem("savedJobs", JSON.stringify(this.getSavedJobs().filter((j) => j.id !== jobId)));
  },
  clearSavedJobs(): void {
    if (typeof window === "undefined") return;
    localStorage.removeItem("savedJobs");
  },
};