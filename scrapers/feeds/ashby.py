"""Ashby JSON feed scraper."""
import asyncio
import httpx
from typing import List, Dict

from scrapers.base import BaseScraper


class AshbyScraper(BaseScraper):
    """Ashby API: https://api.ashbyhq.com/posting-api/job-board/{company}"""
    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{company}"

    def __init__(self, companies: List[str]):
        self.companies = companies

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        total = len(self.companies)
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            for idx, company in enumerate(self.companies, 1):
                try:
                    print(f"  [{idx}/{total}] {company}...", end=" ", flush=True)
                    jobs = await self._scrape_company(client, company)
                    all_jobs.extend(jobs)
                    print(f"{len(jobs)} jobs")
                    await asyncio.sleep(1.5)
                except httpx.TimeoutException:
                    print("TIMEOUT")
                except Exception as e:
                    print(f"ERROR: {e}")
        return all_jobs

    async def _scrape_company(self, client: httpx.AsyncClient, company: str) -> List[Dict]:
        url = self.BASE_URL.format(company=company)
        resp = await client.get(url)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "job_id": f"ash_{job.get('id', hash(str(job.get('title', ''))))}",
                "title": job.get("title", "Unknown"),
                "company": company.replace("-", " ").title(),
                "location": job.get("location", "Remote"),
                "employment_type": job.get("employmentType", "Full-time"),
                "description": job.get("description", ""),
                "requirements": job.get("requirements", ""),
                "apply_url": job.get("applyUrl", ""),
                "source_platform": "ashby",
                "source_url": url,
                "posted_date": job.get("publishedAt", "")
            })
        return jobs
