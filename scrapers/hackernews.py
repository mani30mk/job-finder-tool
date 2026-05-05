"""Hacker News "Who is Hiring" thread scraper."""
import httpx
from selectolax.parser import HTMLParser
from typing import List, Dict
import re


class HNScraper:
    """Scrape latest HN Who is Hiring thread."""

    async def scrape(self) -> List[Dict]:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            # Try to find the latest thread by checking the last few months
            # HN threads are posted on the 1st of each month
            import datetime
            now = datetime.datetime.now()

            # Search for "Who is hiring?" posts via Algolia API
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": "Who is hiring?",
                    "tags": "story",
                    "hitsPerPage": 5
                }
            )
            resp.raise_for_status()
            data = resp.json()

            hits = data.get("hits", [])
            if not hits:
                print("   [HN] No threads found")
                return []

            # Get the most recent "Who is hiring?" thread
            thread_id = None
            for hit in hits:
                title = hit.get("title", "").lower()
                if "who is hiring" in title:
                    thread_id = hit.get("objectID")
                    print(f"   [HN] Found thread: {hit.get('title')} (ID: {thread_id})")
                    break

            if not thread_id:
                print("   [HN] No valid thread found")
                return []

            # Scrape the thread
            return await self._scrape_thread(client, thread_id)

    async def _scrape_thread(self, client: httpx.AsyncClient, thread_id: str) -> List[Dict]:
        url = f"https://news.ycombinator.com/item?id={thread_id}"
        resp = await client.get(url)
        resp.raise_for_status()

        tree = HTMLParser(resp.text)
        jobs = []

        for comment in tree.css(".comtr"):
            text_el = comment.css_first(".commtext")
            if not text_el:
                continue

            text = text_el.text(strip=True)
            if len(text) < 30:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if not lines:
                continue

            first_line = lines[0]
            parts = [p.strip() for p in first_line.split("|")]

            company = parts[0] if parts else "Unknown"
            title = parts[1] if len(parts) > 1 else first_line[:80]
            location = parts[2] if len(parts) > 2 else "Remote"

            urls = re.findall(r'https?://[^\s<>"{}|\^`[\]]+', text)
            apply_url = urls[0] if urls else ""

            jobs.append({
                "job_id": f"hn_{thread_id}_{hash(text) & 0xFFFFFFFF}",
                "title": title[:120],
                "company": company[:80],
                "location": location[:80],
                "employment_type": "Full-time",
                "description": text[:3000],
                "requirements": "",
                "apply_url": apply_url,
                "source_platform": "hackernews",
                "source_url": url,
                "posted_date": ""
            })

        return jobs
