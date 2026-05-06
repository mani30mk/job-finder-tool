"""
Arbeitnow public Job Board API — free, no auth, no rate limits documented.
Jobs sourced directly from ATS (Greenhouse, Lever, etc.) — high quality.
Docs: https://www.arbeitnow.com/api/job-board-api
"""
import httpx
from typing import List, Dict
from datetime import datetime


class ArbeitnowScraper:
    """Scrape jobs from Arbeitnow free public API."""

    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, max_pages: int = 3):
        self.max_pages = max_pages

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        async with httpx.AsyncClient(timeout=20) as client:
            for page in range(1, self.max_pages + 1):
                try:
                    resp = await client.get(
                        self.BASE_URL,
                        params={"page": page},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    jobs = data.get("data", [])
                    if not jobs:
                        break
                    normalized = [self._normalize(j) for j in jobs]
                    all_jobs.extend(normalized)
                    print(f"   [Arbeitnow] Page {page}: {len(jobs)} jobs")
                except Exception as e:
                    print(f"   [Arbeitnow] Page {page} failed: {e}")
                    break

        print(f"   [Arbeitnow] Total: {len(all_jobs)} jobs")
        return all_jobs

    def _normalize(self, job: dict) -> Dict:
        location = "Remote" if job.get("remote") else job.get("location", "")
        return {
            "title":           job.get("title", ""),
            "company":         job.get("company_name", ""),
            "location":        location,
            "employment_type": "full-time",
            "description":     job.get("description", ""),
            "requirements":    "",
            "apply_url":       job.get("url", ""),
            "source_platform": "arbeitnow",
            "posted_date":     datetime.fromtimestamp(
                                   job.get("created_at", 0)
                               ).strftime("%Y-%m-%d") if job.get("created_at") else "",
            "salary":          "",
            "is_new":          1,
            "is_active":       1,
        }
