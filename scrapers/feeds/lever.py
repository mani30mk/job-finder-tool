"""Lever JSON feed scraper."""
import asyncio
import httpx
from typing import List, Dict

from scrapers.base import BaseScraper


class LeverScraper(BaseScraper):
    """Lever API: https://api.lever.co/v0/postings/{company}?mode=json"""
    BASE_URL = "https://api.lever.co/v0/postings/{company}?mode=json"

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
        if resp.status_code in (404, 403):
            return []
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for job in data:
            cats = job.get("categories", {}) or {}
            locs = cats.get("location", ["Remote"])
            location = ", ".join(locs) if isinstance(locs, list) else str(locs)

            reqs = ""
            lists = job.get("lists", [])
            if lists:
                reqs = "\n".join([l.get("content", "") for l in lists if l.get("content")])

            jobs.append({
                "job_id": f"lev_{job.get('id', '')}",
                "title": job.get("text", "Unknown"),
                "company": company.replace("-", " ").title(),
                "location": location,
                "employment_type": cats.get("commitment", "Full-time") if isinstance(cats, dict) else "Full-time",
                "description": job.get("description", ""),
                "requirements": reqs,
                "apply_url": job.get("applyUrl", job.get("hostedUrl", "")),
                "source_platform": "lever",
                "source_url": job.get("hostedUrl", url),
                "posted_date": job.get("createdAt", "")
            })
        return jobs
