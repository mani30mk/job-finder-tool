"""
Freshersworld.com scraper — India-specific board for freshers and campus hiring.
"""
import asyncio
import hashlib
import httpx
from selectolax.parser import HTMLParser
from typing import List, Dict
from datetime import datetime


class FreshersworldScraper:
    """Scrape fresher jobs from Freshersworld.com."""

    SEARCH_URLS = [
        "https://www.freshersworld.com/jobs/jobsearch/Machine-Learning-jobs-for-freshers",
        "https://www.freshersworld.com/jobs/jobsearch/Artificial-Intelligence-jobs-for-freshers",
        "https://www.freshersworld.com/jobs/jobsearch/Data-Science-fresher-jobs",
        "https://www.freshersworld.com/jobs/jobsearch/Software-Engineer-fresher-jobs",
        "https://www.freshersworld.com/jobs/jobsearch/Python-Developer-jobs-for-freshers",
        "https://www.freshersworld.com/jobs/jobsearch/Deep-Learning-fresher-jobs",
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
    }

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True, headers=self.HEADERS
        ) as client:
            for url in self.SEARCH_URLS:
                try:
                    jobs = await self._scrape_page(client, url)
                    all_jobs.extend(jobs)
                    print(f"   [Freshersworld] {len(jobs)} from {url.split('/')[-1][:40]}")
                    await asyncio.sleep(2.0)
                except Exception as e:
                    print(f"   [Freshersworld] Failed: {e}")

        print(f"   [Freshersworld] Total: {len(all_jobs)} jobs")
        return all_jobs

    async def _scrape_page(self, client: httpx.AsyncClient, url: str) -> List[Dict]:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []

        tree = HTMLParser(resp.text)
        jobs = []

        for card in tree.css("div.job-container, div[class*='job-list']"):
            title_el   = card.css_first("h3 a, h2 a, .job-title a")
            company_el = card.css_first(".company-name, .employer")
            loc_el     = card.css_first(".location, .job-location")
            link_el    = card.css_first("a[href*='/jobs/']")

            if not title_el:
                continue

            title   = title_el.text(strip=True)
            company = company_el.text(strip=True) if company_el else "Unknown"
            location = loc_el.text(strip=True) if loc_el else "India"
            link    = link_el.attributes.get("href", "") if link_el else ""
            if link and not link.startswith("http"):
                link = "https://www.freshersworld.com" + link

            job_id = "fw_" + hashlib.md5(
                f"{title}{company}".lower().encode()
            ).hexdigest()[:12]

            jobs.append({
                "job_id":          job_id,
                "title":           title,
                "company":         company,
                "location":        location,
                "employment_type": "internship" if "intern" in title.lower() else "full-time",
                "description":     f"Fresher job listing from Freshersworld. Company: {company}.",
                "requirements":    "",
                "apply_url":       link,
                "source_platform": "freshersworld",
                "posted_date":     datetime.now().strftime("%Y-%m-%d"),
                "salary":          "",
                "is_new":          1,
                "is_active":       1,
            })

        return jobs
