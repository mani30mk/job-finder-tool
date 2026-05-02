"""Internshala scraper."""
import asyncio
import httpx
from selectolax.parser import HTMLParser
from typing import List, Dict

from app_config.settings import REQUEST_DELAY
from scrapers.base import BaseScraper


class InternshalaScraper(BaseScraper):
    BASE_URL = "https://internshala.com/internships/keywords-{query}/page-{page}/"

    def __init__(self, queries: List[str] = None, max_pages: int = 3):
        self.queries = queries or ["software", "web-development", "data-science"]
        self.max_pages = max_pages

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for query in self.queries:
                for page in range(1, self.max_pages + 1):
                    try:
                        jobs = await self._scrape_page(client, query, page)
                        all_jobs.extend(jobs)
                        if not jobs:
                            break
                        await asyncio.sleep(REQUEST_DELAY[0])
                    except Exception as e:
                        print(f"[Internshala] Error page {page}: {e}")
                        break
        return all_jobs

    async def _scrape_page(self, client: httpx.AsyncClient, query: str, page: int) -> List[Dict]:
        url = self.BASE_URL.format(query=query, page=page)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml"
        }
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()

        tree = HTMLParser(resp.text)
        jobs = []

        for card in tree.css(".individual_internship"):
            title_el = card.css_first(".job-internship-name")
            company_el = card.css_first(".company-name")
            loc_el = card.css_first("#location_names")
            link_el = card.css_first("a")

            if not title_el or not link_el:
                continue

            title = title_el.text(strip=True)
            company = company_el.text(strip=True) if company_el else "Unknown"
            location = loc_el.text(strip=True) if loc_el else "Remote"
            link = "https://internshala.com" + link_el.attributes.get("href", "")

            jobs.append({
                "job_id": f"is_{hash(link) & 0xFFFFFFFF}",
                "title": title,
                "company": company,
                "location": location,
                "employment_type": "Internship",
                "description": "",
                "requirements": "",
                "apply_url": link,
                "source_platform": "internshala",
                "source_url": url,
                "posted_date": ""
            })
        return jobs
