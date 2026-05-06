"""
Remotive public API scraper — free, no API key required.
Returns remote tech jobs. JSON API, no scraping.
Docs: https://remotive.com/api/remote-jobs
"""
import httpx
from typing import List, Dict
from datetime import datetime


class RemotiveScraper:
    """Scrape jobs from Remotive public API."""

    BASE_URL = "https://remotive.com/api/remote-jobs"
    CATEGORIES = [
        "software-dev",
        "data",
        "devops",
        "product",
    ]

    def __init__(self, limit: int = 100):
        self.limit = limit

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        async with httpx.AsyncClient(timeout=20) as client:
            for category in self.CATEGORIES:
                try:
                    resp = await client.get(
                        self.BASE_URL,
                        params={"category": category, "limit": 50},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    jobs = data.get("jobs", [])
                    normalized = [self._normalize(j) for j in jobs]
                    all_jobs.extend(normalized)
                    print(f"   [Remotive] {category}: {len(jobs)} jobs")
                except Exception as e:
                    print(f"   [Remotive] {category} failed: {e}")

        print(f"   [Remotive] Total: {len(all_jobs)} jobs")
        return all_jobs[:self.limit]

    def _normalize(self, job: dict) -> Dict:
        return {
            "title":           job.get("title", ""),
            "company":         job.get("company_name", ""),
            "location":        job.get("candidate_required_location", "Worldwide"),
            "employment_type": job.get("job_type", "full_time").replace("_", "-"),
            "description":     job.get("description", ""),
            "requirements":    "",
            "apply_url":       job.get("url", ""),
            "source_platform": "remotive",
            "posted_date":     job.get("publication_date", datetime.now().isoformat())[:10],
            "salary":          job.get("salary", ""),
            "is_new":          1,
            "is_active":       1,
        }
