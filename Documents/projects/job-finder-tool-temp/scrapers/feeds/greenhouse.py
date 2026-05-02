"""Greenhouse JSON feed scraper - uses official Job Board API."""
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict

from scrapers.base import BaseScraper


class GreenhouseScraper(BaseScraper):
    """Official Greenhouse Job Board API: https://developers.greenhouse.io/job-board.html"""
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

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
        resp = await client.get(url, params={"content": "true"})

        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for job in data.get("jobs", []):
            locs = job.get("location", {})
            location = locs.get("name", "Remote") if isinstance(locs, dict) else str(locs)

            # Get apply URL
            apply_url = ""
            for link in job.get("absolute_url", []):
                if isinstance(link, str):
                    apply_url = link
                    break
            if not apply_url:
                apply_url = job.get("absolute_url", "")

            jobs.append({
                "job_id": f"gh_{job.get('id', '')}",
                "title": job.get("title", "Unknown"),
                "company": company.replace("-", " ").title(),
                "location": location,
                "employment_type": self._detect_type(job.get("title", "")),
                "description": self._clean_html(job.get("content", "")),
                "requirements": "",
                "apply_url": apply_url,
                "source_platform": "greenhouse",
                "source_url": url,
                "posted_date": job.get("updated_at", datetime.now().isoformat())
            })
        return jobs

    def _detect_type(self, title: str) -> str:
        t = title.lower()
        if any(x in t for x in ["intern", "internship", "trainee", "fellow"]):
            return "Internship"
        if any(x in t for x in ["contract", "freelance", "consultant"]):
            return "Contract"
        if any(x in t for x in ["part-time", "part time", "half-time"]):
            return "Part-time"
        return "Full-time"

    def _clean_html(self, html: str) -> str:
        from selectolax.parser import HTMLParser
        if not html:
            return ""
        tree = HTMLParser(html)
        return tree.text(separator="\n").strip()
