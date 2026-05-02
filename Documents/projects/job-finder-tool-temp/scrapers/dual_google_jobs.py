"""Dual-API Google Jobs scraper — SerpApi + TheirStack with auto-fallback.

Strategy:
1. Try SerpApi first (100 free searches/month)
2. If SerpApi fails/quota exceeded, switch to TheirStack (200 free credits/month)
3. Track usage to respect limits
4. Combine results, deduplicate across both APIs

Usage:
    from scrapers.dual_google_jobs import DualGoogleJobsScraper
    scraper = DualGoogleJobsScraper(
        serpapi_key="your_serpapi_key",
        theirstack_key="your_theirstack_key",
        query="software engineer",
        num_results=30,
    )
    jobs = await scraper.scrape()
"""
import httpx
import os
from typing import List, Dict, Optional
from datetime import datetime


class QuotaTracker:
    """Simple file-based quota tracker to avoid hitting API limits."""

    def __init__(self, tracker_file: str = ".api_quota_tracker.json"):
        self.tracker_file = tracker_file
        self.usage = self._load()

    def _load(self) -> Dict:
        import json
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {
            "serpapi": {"month": datetime.now().month, "count": 0},
            "theirstack": {"month": datetime.now().month, "count": 0},
        }

    def _save(self):
        import json
        with open(self.tracker_file, "w") as f:
            json.dump(self.usage, f)

    def check_serpapi(self, limit: int = 100) -> bool:
        """Check if SerpApi has quota remaining."""
        current_month = datetime.now().month
        if self.usage["serpapi"]["month"] != current_month:
            self.usage["serpapi"] = {"month": current_month, "count": 0}
        return self.usage["serpapi"]["count"] < limit

    def check_theirstack(self, limit: int = 200) -> bool:
        """Check if TheirStack has quota remaining."""
        current_month = datetime.now().month
        if self.usage["theirstack"]["month"] != current_month:
            self.usage["theirstack"] = {"month": current_month, "count": 0}
        return self.usage["theirstack"]["count"] < limit

    def increment(self, api: str):
        """Record an API call."""
        self.usage[api]["count"] += 1
        self._save()

    def get_status(self) -> Dict:
        """Get current quota status."""
        return {
            "serpapi": {
                "used": self.usage["serpapi"]["count"],
                "limit": 100,
                "remaining": max(0, 100 - self.usage["serpapi"]["count"]),
            },
            "theirstack": {
                "used": self.usage["theirstack"]["count"],
                "limit": 200,
                "remaining": max(0, 200 - self.usage["theirstack"]["count"]),
            },
        }


class DualGoogleJobsScraper:
    """
    Scrape Google Jobs via SerpApi, fallback to TheirStack.

    Combines the best of both:
    - SerpApi: Broad coverage (LinkedIn, Indeed, Glassdoor, etc.)
    - TheirStack: Tech-focused, salary data, tech stack info
    """

    def __init__(
        self,
        serpapi_key: str = "",
        theirstack_key: str = "",
        query: str = "software engineer",
        location: str = "",
        country: str = "us",
        num_results: int = 30,
        employment_type: str = "",  # FULLTIME, PARTTIME, CONTRACTOR, INTERN
        date_posted: str = "",  # today, 3days, week, month
        remote_only: bool = False,
        tracker_file: str = ".api_quota_tracker.json",
    ):
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_KEY", "")
        self.theirstack_key = theirstack_key or os.getenv("THEIRSTACK_KEY", "")
        self.query = query
        self.location = location
        self.country = country
        self.num_results = num_results
        self.employment_type = employment_type
        self.date_posted = date_posted
        self.remote_only = remote_only
        self.tracker = QuotaTracker(tracker_file)

    async def scrape(self) -> List[Dict]:
        """Scrape jobs using available APIs with auto-fallback."""
        all_jobs = []
        status = self.tracker.get_status()

        print(f"\n   [Dual API] Quota status:")
        print(f"      SerpApi: {status['serpapi']['used']}/100 used, {status['serpapi']['remaining']} left")
        print(f"      TheirStack: {status['theirstack']['used']}/200 used, {status['theirstack']['remaining']} left")

        # --- Strategy 1: SerpApi (broader coverage) ---
        if self.serpapi_key and self.serpapi_key != "YOUR_SERPAPI_KEY" and status["serpapi"]["remaining"] > 0:
            print(f"\n   [Dual API] Trying SerpApi...")
            try:
                jobs = await self._scrape_serpapi()
                if jobs:
                    all_jobs.extend(jobs)
                    print(f"   ✅ SerpApi: {len(jobs)} jobs")
                else:
                    print(f"   ⚠️ SerpApi returned 0 jobs")
            except Exception as e:
                err = str(e)
                if "quota" in err.lower() or "limit" in err.lower() or "exceeded" in err.lower():
                    print(f"   ❌ SerpApi quota exceeded")
                else:
                    print(f"   ❌ SerpApi error: {e}")
        else:
            print(f"\n   [Dual API] Skipping SerpApi (no key or quota exhausted)")

        # --- Strategy 2: TheirStack (tech-focused, fallback) ---
        remaining_needed = self.num_results - len(all_jobs)
        if remaining_needed > 0 and self.theirstack_key and self.theirstack_key != "YOUR_THEIRSTACK_KEY" and status["theirstack"]["remaining"] > 0:
            print(f"\n   [Dual API] Trying TheirStack (need {remaining_needed} more)...")
            try:
                jobs = await self._scrape_theirstack(limit=remaining_needed)
                if jobs:
                    all_jobs.extend(jobs)
                    print(f"   ✅ TheirStack: {len(jobs)} jobs")
                else:
                    print(f"   ⚠️ TheirStack returned 0 jobs")
            except Exception as e:
                err = str(e)
                if "quota" in err.lower() or "limit" in err.lower() or "exceeded" in err.lower():
                    print(f"   ❌ TheirStack quota exceeded")
                else:
                    print(f"   ❌ TheirStack error: {e}")
        elif len(all_jobs) >= self.num_results:
            print(f"\n   [Dual API] Already have {len(all_jobs)} jobs, skipping TheirStack")
        else:
            print(f"\n   [Dual API] Skipping TheirStack (no key or quota exhausted)")

        # --- Deduplicate across both APIs ---
        unique_jobs = self._deduplicate(all_jobs)
        print(f"\n   [Dual API] Combined: {len(all_jobs)} raw | {len(unique_jobs)} unique")

        return unique_jobs[:self.num_results]

    async def _scrape_serpapi(self) -> List[Dict]:
        """Scrape via SerpApi Google Jobs."""
        url = "https://serpapi.com/search"
        params = {
            "engine": "google_jobs",
            "q": self.query,
            "location": self.location,
            "google_domain": f"google.{self.country}",
            "hl": "en",
            "api_key": self.serpapi_key,
        }
        if self.employment_type:
            params["employment_type"] = self.employment_type
        if self.date_posted:
            params["date_posted"] = self.date_posted

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        self.tracker.increment("serpapi")

        jobs = []
        for job in data.get("jobs_results", []):
            extensions = job.get("extensions", [])
            company = "Unknown"
            location = "Remote"
            posted_date = ""
            employment_type = "Full-time"

            for ext in extensions:
                ext_lower = str(ext).lower()
                if "ago" in ext_lower or "day" in ext_lower or "hour" in ext_lower:
                    posted_date = ext
                elif any(x in ext_lower for x in ["remote", "hybrid", "on-site", "onsite"]):
                    location = ext
                elif any(x in ext_lower for x in ["full-time", "part-time", "contract", "internship"]):
                    employment_type = ext
                elif company == "Unknown" and len(str(ext)) < 50:
                    company = ext

            detected = job.get("detected_extensions", {})
            if detected.get("posted_at"):
                posted_date = detected["posted_at"]
            if detected.get("schedule_type"):
                employment_type = detected["schedule_type"]

            highlights = job.get("job_highlights", [])
            requirements = ""
            for section in highlights:
                title = section.get("title", "").lower()
                if any(x in title for x in ["qualification", "requirement", "skills", "experience"]):
                    items = section.get("items", [])
                    requirements = " | ".join(items)[:2000]

            jobs.append({
                "job_id": f"serp_{job.get('job_id', hash(job.get('title', '')))}",
                "title": job.get("title", "Unknown")[:200],
                "company": company[:100],
                "location": location[:100],
                "employment_type": employment_type,
                "description": str(job.get("description", ""))[:4000],
                "requirements": requirements,
                "apply_url": job.get("apply_link", job.get("share_link", "")),
                "source_platform": "serpapi_google",
                "source_url": job.get("share_link", ""),
                "posted_date": posted_date,
                "salary": detected.get("salary", ""),
            })

        return jobs

    async def _scrape_theirstack(self, limit: int = 50) -> List[Dict]:
        """Scrape via TheirStack API."""
        url = "https://api.theirstack.com/jobs/search"
        headers = {
            "Authorization": f"Bearer {self.theirstack_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": self.query,
            "limit": limit,
            "posted_within_days": 30,
        }
        if self.location:
            payload["location"] = self.location
        if self.remote_only:
            payload["remote_only"] = True

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        self.tracker.increment("theirstack")

        jobs = []
        for job in data.get("data", []):
            company = job.get("company", {})
            location_data = job.get("location", {})
            salary = job.get("salary", {})
            tech_stack = job.get("tech_stack", [])

            apply_url = job.get("url", "")
            if not apply_url and job.get("id"):
                apply_url = f"https://theirstack.com/jobs/{job['id']}"

            jobs.append({
                "job_id": f"ts_{job.get('id', '')}",
                "title": job.get("title", "Unknown")[:200],
                "company": company.get("name", "Unknown")[:100],
                "location": location_data.get("display_name", "Remote")[:100],
                "employment_type": job.get("employment_type", "Full-time"),
                "description": str(job.get("description", ""))[:4000],
                "requirements": " | ".join(tech_stack)[:2000] if tech_stack else "",
                "apply_url": apply_url,
                "source_platform": "theirstack",
                "source_url": apply_url,
                "posted_date": job.get("date_posted", ""),
                "salary_min": salary.get("min", ""),
                "salary_max": salary.get("max", ""),
                "salary_currency": salary.get("currency", ""),
                "remote_policy": job.get("remote_policy", ""),
                "seniority": job.get("seniority", ""),
            })

        return jobs

    def _deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicates across both APIs by title+company hash."""
        seen = set()
        unique = []
        for job in jobs:
            key = f"{job.get('title', '').lower().strip()}|{job.get('company', '').lower().strip()}"
            if key not in seen:
                seen.add(key)
                unique.append(job)
        return unique

    def get_quota_status(self) -> Dict:
        """Get current quota status for both APIs."""
        return self.tracker.get_status()
