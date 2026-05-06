"""
Naukri.com HTML scraper — India's largest job board.
No official API. Uses httpx + selectolax (same as internshala.py).
Targets: fresher / intern / entry-level jobs in India.
"""
import asyncio
import hashlib
import httpx
from selectolax.parser import HTMLParser
from typing import List, Dict
from datetime import datetime


class NaukriScraper:
    """Scrape fresher/intern jobs from Naukri.com."""

    SEARCH_URLS = [
        "https://www.naukri.com/machine-learning-jobs-in-india?experience=0&jobAge=7",
        "https://www.naukri.com/deep-learning-jobs?experience=0&jobAge=7",
        "https://www.naukri.com/data-science-jobs-in-india?experience=0&jobAge=7",
        "https://www.naukri.com/software-developer-jobs-for-freshers?jobAge=7",
        "https://www.naukri.com/python-developer-jobs-in-india?experience=0&jobAge=7",
        "https://www.naukri.com/machine-learning-internship-jobs?jobAge=7",
        "https://www.naukri.com/software-engineer-internship-jobs?jobAge=7",
        "https://www.naukri.com/artificial-intelligence-jobs-in-india?experience=0",
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.naukri.com/",
    }

    def __init__(self, delay: float = 3.0):
        self.delay = delay

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers=self.HEADERS,
        ) as client:
            for url in self.SEARCH_URLS:
                try:
                    jobs = await self._scrape_page(client, url)
                    all_jobs.extend(jobs)
                    print(f"   [Naukri] {len(jobs)} jobs from {url.split('?')[0].split('/')[-1]}")
                    await asyncio.sleep(self.delay)
                except Exception as e:
                    print(f"   [Naukri] Failed {url[:60]}: {e}")

        print(f"   [Naukri] Total: {len(all_jobs)} jobs")
        return all_jobs

    async def _scrape_page(self, client: httpx.AsyncClient, url: str) -> List[Dict]:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []

        tree = HTMLParser(resp.text)
        jobs = []

        # Naukri job cards selector (check for updates if Naukri changes layout)
        for card in tree.css("article.jobTuple, div.jobTuple, div[class*='jobTuple']"):
            try:
                title_el  = card.css_first("a.title, a[class*='title']")
                company_el = card.css_first("a.subTitle, span[class*='comp-name']")
                loc_el    = card.css_first("li.location, span[class*='locWdth']")
                exp_el    = card.css_first("li.experience, span[class*='expwdth']")
                link_el   = card.css_first("a.title, a[class*='title']")

                if not title_el:
                    continue

                title   = title_el.text(strip=True)
                company = company_el.text(strip=True) if company_el else "Unknown"
                location = loc_el.text(strip=True) if loc_el else "India"
                exp     = exp_el.text(strip=True) if exp_el else "Fresher"
                link    = link_el.attributes.get("href", "") if link_el else ""
                if link and not link.startswith("http"):
                    link = "https://www.naukri.com" + link

                # Generate stable ID from title+company
                job_id = "naukri_" + hashlib.md5(
                    f"{title}{company}".lower().encode()
                ).hexdigest()[:12]

                jobs.append({
                    "job_id":          job_id,
                    "title":           title,
                    "company":         company,
                    "location":        location,
                    "employment_type": "internship" if "intern" in title.lower() else "full-time",
                    "description":     f"Experience: {exp}. Posted on Naukri.com India.",
                    "requirements":    "",
                    "apply_url":       link,
                    "source_platform": "naukri",
                    "posted_date":     datetime.now().strftime("%Y-%m-%d"),
                    "salary":          "",
                    "is_new":          1,
                    "is_active":       1,
                })
            except Exception:
                continue

        return jobs
