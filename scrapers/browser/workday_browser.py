"""Workday job board scraper using Playwright."""
import asyncio
import random
from typing import List, Dict

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

from app_config.settings import REQUEST_DELAY, WORKDAY_MAX_JOBS
from scrapers.base import BaseScraper


class WorkdayScraper(BaseScraper):
    def __init__(self, company_domains: List[str]):
        self.company_domains = company_domains

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        for domain in self.company_domains:
            try:
                jobs = await self._scrape_domain(domain)
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"[Workday] Error {domain}: {e}")
        return all_jobs

    async def _scrape_domain(self, company_domain: str) -> List[Dict]:
        company = company_domain.split(".")[0]

        # Try common Workday URL patterns
        urls_to_try = [
            f"https://{company_domain}/en-US/{company}/jobs",
            f"https://{company_domain}/en-US/external",
            f"https://{company_domain}/en-US/search",
            f"https://{company_domain}/{company}/jobs",
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            await stealth_async(page)

            jobs = []

            for url in urls_to_try:
                try:
                    print(f"[Workday] Trying {url}")
                    resp = await page.goto(url, wait_until="networkidle", timeout=30000)
                    if resp and resp.status == 404:
                        continue
                    await asyncio.sleep(5)
                    break
                except Exception:
                    continue
            else:
                print(f"[Workday] Could not find valid URL for {company_domain}")
                await browser.close()
                return []

            # Scroll to load more jobs
            prev_count = 0
            for _ in range(15):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                # Try multiple selectors
                selectors = [
                    "[data-automation-id='jobListing']",
                    "[data-automation-id='jobTile']",
                    ".css-1q2dra3",  # common workday class
                    "[role='listitem']"
                ]

                cards = []
                for sel in selectors:
                    cards = await page.query_selector_all(sel)
                    if cards:
                        break

                if len(cards) == prev_count or len(cards) >= WORKDAY_MAX_JOBS:
                    break
                prev_count = len(cards)

            print(f"[Workday] {company}: Found {len(cards)} jobs")

            for card in cards[:WORKDAY_MAX_JOBS]:
                try:
                    title = await card.query_selector_eval("h3, h2, a", "el => el.innerText")
                    loc = await card.query_selector_eval(
                        "[data-automation-id='jobLocations'], [data-automation-id='location']",
                        "el => el.innerText"
                    )
                    link = await card.query_selector_eval("a", "el => el.href")

                    if title and link:
                        jobs.append({
                            "job_id": f"wd_{hash(link) & 0xFFFFFFFF}",
                            "title": title.strip()[:200],
                            "company": company.upper(),
                            "location": (loc or "Remote").strip()[:100],
                            "employment_type": "Full-time",
                            "description": "",
                            "requirements": "",
                            "apply_url": link,
                            "source_platform": "workday",
                            "source_url": url,
                            "posted_date": ""
                        })
                except:
                    continue

            await browser.close()
            return jobs
