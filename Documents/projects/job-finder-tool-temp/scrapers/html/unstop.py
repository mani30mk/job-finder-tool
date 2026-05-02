"""Unstop (formerly Dare2Compete) scraper."""
import asyncio
import httpx
from typing import List, Dict

from app_config.settings import REQUEST_DELAY
from scrapers.base import BaseScraper


class UnstopScraper(BaseScraper):
    SEARCH_URL = "https://unstop.com/api/public/opportunity/search"

    def __init__(self, queries: List[str] = None, max_pages: int = 3):
        self.queries = queries or ["software engineer", "internship"]
        self.max_pages = max_pages

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for query in self.queries:
                for page in range(1, self.max_pages + 1):
                    try:
                        jobs = await self._search_page(client, query, page)
                        all_jobs.extend(jobs)
                        if not jobs:
                            break
                        await asyncio.sleep(REQUEST_DELAY[0])
                    except Exception as e:
                        print(f"[Unstop] Error page {page}: {e}")
                        break
        return all_jobs

    async def _search_page(self, client: httpx.AsyncClient, query: str, page: int) -> List[Dict]:
        payload = {
            "filters": [],
            "page": page,
            "search": query,
            "oppstatus": "open",
            "sort": "recent"
        }
        resp = await client.post(self.SEARCH_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        opps = data.get("data", {}).get("data", [])
        for opp in opps:
            org = opp.get("organisation", {}) or {}
            jobs.append({
                "job_id": f"unstop_{opp.get('id', '')}",
                "title": opp.get("title", "Unknown"),
                "company": org.get("name", "Unknown") if isinstance(org, dict) else "Unknown",
                "location": opp.get("venue", opp.get("region", "Remote")),
                "employment_type": opp.get("category", "Internship"),
                "description": str(opp.get("description", ""))[:3000],
                "requirements": "",
                "apply_url": f"https://unstop.com{opp.get('seo_url', '')}",
                "source_platform": "unstop",
                "source_url": f"https://unstop.com{opp.get('seo_url', '')}",
                "posted_date": opp.get("regn_start_date", opp.get("start_date", ""))
            })
        return jobs
