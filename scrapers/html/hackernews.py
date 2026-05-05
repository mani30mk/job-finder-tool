"""Hacker News "Who is Hiring" thread scraper."""
import httpx
from selectolax.parser import HTMLParser
from typing import List, Dict
import re

from scrapers.base import BaseScraper


class HNScraper(BaseScraper):
    BASE_URL = "https://news.ycombinator.com/item?id={thread_id}"

    def __init__(self, thread_ids: List[int] = None):
        # Default: check https://news.ycombinator.com/submitted?id=whoishiring for latest
        self.thread_ids = thread_ids or [43789234]

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for tid in self.thread_ids:
                try:
                    jobs = await self._scrape_thread(client, tid)
                    all_jobs.extend(jobs)
                except Exception as e:
                    print(f"[HN] Error thread {tid}: {e}")
        return all_jobs

    async def _scrape_thread(self, client: httpx.AsyncClient, thread_id: int) -> List[Dict]:
        url = self.BASE_URL.format(thread_id=thread_id)
        resp = await client.get(url)
        resp.raise_for_status()

        tree = HTMLParser(resp.text)
        jobs = []

        for comment in tree.css(".comtr"):
            text_el = comment.css_first(".commtext")
            if not text_el:
                continue

            text = text_el.text(strip=True)
            if len(text) < 50:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if not lines:
                continue

            # First line usually: "CompanyName | Position | Location"
            first_line = lines[0]
            parts = [p.strip() for p in first_line.split("|")]

            company = parts[0] if parts else "Unknown"
            title = parts[1] if len(parts) > 1 else first_line[:80]
            location = parts[2] if len(parts) > 2 else "Remote/Various"

            # Try to find URL in text
            urls = re.findall(r'https?://[^\s<>"{}|\^`[\]]+', text)
            apply_url = urls[0] if urls else ""

            jobs.append({
                "job_id": f"hn_{thread_id}_{hash(text) & 0xFFFFFFFF}",
                "title": title[:120],
                "company": company[:80],
                "location": location[:80],
                "employment_type": "Full-time",
                "description": text[:4000],
                "requirements": "",
                "apply_url": apply_url,
                "source_platform": "hackernews",
                "source_url": url,
                "posted_date": ""
            })
        return jobs
