"""Triple-API Google Jobs scraper — SerpApi + JSearch + TheirStack with auto-fallback.

FIXED v3:
- SerpApi: Uses correct endpoint /search.json and google_domain=google.com
- TheirStack: Uses correct base URL https://api.theirstack.com/v1 and proper payload
- Quota only counts SUCCESSFUL requests
"""
import httpx
import os
import json
from typing import List, Dict
from datetime import datetime


class QuotaTracker:
    """File-based quota tracker — only counts SUCCESSFUL requests."""

    def __init__(self, tracker_file: str = ".api_quota_tracker.json"):
        self.tracker_file = tracker_file
        self.usage = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {
            "serpapi": {"month": datetime.now().month, "count": 0},
            "jsearch": {"month": datetime.now().month, "count": 0},
            "theirstack": {"month": datetime.now().month, "count": 0},
        }

    def _save(self):
        with open(self.tracker_file, "w") as f:
            json.dump(self.usage, f)

    def check(self, api: str, limit: int) -> bool:
        current_month = datetime.now().month
        if self.usage[api]["month"] != current_month:
            self.usage[api] = {"month": current_month, "count": 0}
        return self.usage[api]["count"] < limit

    def increment(self, api: str):
        self.usage[api]["count"] += 1
        self._save()

    def reset(self, api: str = None):
        if api:
            self.usage[api] = {"month": datetime.now().month, "count": 0}
        else:
            for key in self.usage:
                self.usage[key] = {"month": datetime.now().month, "count": 0}
        self._save()

    def get_status(self) -> Dict:
        return {
            "serpapi": {
                "used": self.usage["serpapi"]["count"],
                "limit": 100,
                "remaining": max(0, 100 - self.usage["serpapi"]["count"]),
            },
            "jsearch": {
                "used": self.usage["jsearch"]["count"],
                "limit": 200,
                "remaining": max(0, 200 - self.usage["jsearch"]["count"]),
            },
            "theirstack": {
                "used": self.usage["theirstack"]["count"],
                "limit": 200,
                "remaining": max(0, 200 - self.usage["theirstack"]["count"]),
            },
        }


class TripleGoogleJobsScraper:
    """Scrape Google Jobs via 3 APIs with auto-fallback."""

    def __init__(
        self,
        serpapi_key: str = "",
        jsearch_key: str = "",
        theirstack_key: str = "",
        query: str = "software engineer",
        location: str = "",
        country: str = "us",
        num_results: int = 50,
        employment_type: str = "",
        date_posted: str = "",
        remote_only: bool = False,
        tracker_file: str = ".api_quota_tracker.json",
    ):
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_KEY", "")
        self.jsearch_key = jsearch_key or os.getenv("RAPIDAPI_KEY", "")
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
        all_jobs = []
        status = self.tracker.get_status()

        print(f"   [Triple API] Quota status:")
        print(f"      SerpApi:    {status['serpapi']['used']}/100 used, {status['serpapi']['remaining']} left")
        print(f"      JSearch:    {status['jsearch']['used']}/200 used, {status['jsearch']['remaining']} left")
        print(f"      TheirStack: {status['theirstack']['used']}/200 used, {status['theirstack']['remaining']} left")

        # Strategy 1: SerpApi
        has_serpapi = bool(self.serpapi_key and self.serpapi_key != "YOUR_SERPAPI_KEY")
        if has_serpapi and status["serpapi"]["remaining"] > 0:
            print(f"\n   [Triple API] Trying SerpApi...")
            try:
                jobs = await self._scrape_serpapi()
                if jobs:
                    all_jobs.extend(jobs)
                    self.tracker.increment("serpapi")
                    print(f"   Got {len(jobs)} jobs from SerpApi")
                else:
                    print(f"   SerpApi returned 0 jobs")
            except Exception as e:
                print(f"   SerpApi failed: {e}")
        else:
            reason = "quota exhausted" if has_serpapi else "no key configured"
            print(f"\n   [Triple API] Skipping SerpApi ({reason})")

        # Strategy 2: JSearch
        remaining_needed = self.num_results - len(all_jobs)
        has_jsearch = bool(self.jsearch_key and self.jsearch_key != "YOUR_RAPIDAPI_KEY")
        if remaining_needed > 0 and has_jsearch and status["jsearch"]["remaining"] > 0:
            print(f"\n   [Triple API] Trying JSearch (need {remaining_needed} more)...")
            try:
                jobs = await self._scrape_jsearch(limit=remaining_needed)
                if jobs:
                    all_jobs.extend(jobs)
                    self.tracker.increment("jsearch")
                    print(f"   Got {len(jobs)} jobs from JSearch")
                else:
                    print(f"   JSearch returned 0 jobs")
            except Exception as e:
                print(f"   JSearch failed: {e}")
        elif len(all_jobs) >= self.num_results:
            print(f"\n   [Triple API] Already have {len(all_jobs)} jobs, skipping JSearch")

        # Strategy 3: TheirStack
        remaining_needed = self.num_results - len(all_jobs)
        has_theirstack = bool(self.theirstack_key and self.theirstack_key != "YOUR_THEIRSTACK_KEY")
        if remaining_needed > 0 and has_theirstack and status["theirstack"]["remaining"] > 0:
            print(f"\n   [Triple API] Trying TheirStack (need {remaining_needed} more)...")
            try:
                jobs = await self._scrape_theirstack(limit=remaining_needed)
                if jobs:
                    all_jobs.extend(jobs)
                    self.tracker.increment("theirstack")
                    print(f"   Got {len(jobs)} jobs from TheirStack")
                else:
                    print(f"   TheirStack returned 0 jobs")
            except Exception as e:
                print(f"   TheirStack failed: {e}")
        elif len(all_jobs) >= self.num_results:
            print(f"\n   [Triple API] Already have {len(all_jobs)} jobs, skipping TheirStack")

        # Deduplicate
        unique_jobs = self._deduplicate(all_jobs)
        print(f"\n   [Triple API] Combined: {len(all_jobs)} raw | {len(unique_jobs)} unique")

        return unique_jobs[:self.num_results]

    async def _scrape_serpapi(self) -> List[Dict]:
        """Scrape via SerpApi Google Jobs — FIXED endpoint and domain."""
        # FIXED: Use search.json endpoint and google.com domain
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": self.query,
            "google_domain": "google.com",  # FIXED: was google.us
            "hl": "en",
            "api_key": self.serpapi_key,
        }
        # Only add location if provided (must be a valid city like "Austin, Texas")
        if self.location and self.location.strip():
            params["location"] = self.location
        if self.employment_type:
            params["employment_type"] = self.employment_type
        if self.date_posted:
            params["date_posted"] = self.date_posted

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        # Check for API errors in response
        if "error" in data:
            raise Exception(f"SerpApi error: {data['error']}")

        jobs = []
        for job in data.get("jobs_results", []):
            extensions = job.get("extensions", [])
            company = job.get("company_name", "Unknown")
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

    async def _scrape_jsearch(self, limit: int = 50) -> List[Dict]:
        """Scrape via JSearch API (RapidAPI)."""
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": self.jsearch_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        params = {
            "query": self.query,
            "page": 1,
            "num_pages": 1,
            "country": self.country.lower(),
        }
        if self.location and self.location.strip():
            params["location"] = self.location
        if self.remote_only:
            params["remote_jobs_only"] = "true"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") == "ERROR":
            err = data.get("error", {})
            raise Exception(f"JSearch API error: {err.get('message', 'Unknown')}")

        jobs = []
        for job in data.get("data", [])[:limit]:
            apply_options = job.get("apply_options", [])
            apply_url = apply_options[0].get("link", "") if apply_options else ""
            if not apply_url:
                apply_url = job.get("job_apply_link", job.get("job_google_link", ""))

            jobs.append({
                "job_id": f"jsearch_{job.get('job_id', '')}",
                "title": job.get("job_title", "Unknown")[:200],
                "company": job.get("employer_name", "Unknown")[:100],
                "location": job.get("job_location", "Remote")[:100],
                "employment_type": job.get("job_employment_type", "Full-time"),
                "description": str(job.get("job_description", ""))[:4000],
                "requirements": str(job.get("job_highlights", {}).get("Qualifications", ""))[:2000],
                "apply_url": apply_url,
                "source_platform": "jsearch",
                "source_url": job.get("job_google_link", ""),
                "posted_date": job.get("job_posted_at_datetime_utc", ""),
                "salary_min": job.get("job_min_salary", ""),
                "salary_max": job.get("job_max_salary", ""),
                "salary_currency": job.get("job_salary_currency", ""),
                "salary_period": job.get("job_salary_period", ""),
                "is_remote": job.get("job_is_remote", False),
                "company_logo": job.get("employer_logo", ""),
            })

        return jobs

    async def _scrape_theirstack(self, limit: int = 50) -> List[Dict]:
        """Scrape via TheirStack API — FIXED base URL and payload."""
        # FIXED: Use https://api.theirstack.com/v1 base URL
        url = "https://api.theirstack.com/v1/jobs/search"
        headers = {
            "Authorization": f"Bearer {self.theirstack_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # FIXED: Use proper payload structure from TheirStack docs
        payload = {
            "order_by": [
                {"desc": True, "field": "date_posted"},
                {"desc": True, "field": "discovered_at"},
            ],
            "page": 0,
            "limit": limit,
            "job_title_or": [self.query] if self.query else [],
            "job_country_code_or": [self.country.upper()] if self.country else [],
            "posted_at_max_age_days": 30,
            "remote": self.remote_only,
            "include_total_results": False,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

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
        seen = set()
        unique = []
        for job in jobs:
            key = f"{job.get('title', '').lower().strip()}|{job.get('company', '').lower().strip()}"
            if key not in seen:
                seen.add(key)
                unique.append(job)
        return unique

    def get_quota_status(self) -> Dict:
        return self.tracker.get_status()