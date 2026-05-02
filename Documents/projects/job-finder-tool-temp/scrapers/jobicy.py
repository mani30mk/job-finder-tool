"""Jobicy scraper — free remote jobs API, no auth required."""
import httpx
from typing import List, Dict


class JobicyScraper:
    """Scrape remote jobs from Jobicy API.

    API docs: https://jobicy.com/api/v2/remote-jobs
    No authentication required. Free to use.
    """

    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    def __init__(self, count: int = 50, geo: str = "", industry: str = "", tag: str = ""):
        self.count = min(count, 100)  # Max 100 per request
        self.geo = geo
        self.industry = industry
        self.tag = tag

    async def scrape(self) -> List[Dict]:
        params = {
            "count": self.count,
            "geo": self.geo,
            "industry": self.industry,
            "tag": self.tag,
        }
        # Remove empty params
        params = {k: v for k, v in params.items() if v}

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "job_id": f"jobicy_{job.get('id', '')}",
                "title": job.get("jobTitle", "Unknown")[:200],
                "company": job.get("companyName", "Unknown")[:100],
                "location": job.get("jobGeo", "Remote")[:100],
                "employment_type": job.get("jobType", "Remote"),
                "description": str(job.get("jobDesc", ""))[:3000],
                "requirements": "",
                "apply_url": job.get("url", ""),
                "source_platform": "jobicy",
                "source_url": job.get("url", ""),
                "posted_date": job.get("pubDate", ""),
                "salary": job.get("annualSalaryMin", ""),
            })

        return jobs
