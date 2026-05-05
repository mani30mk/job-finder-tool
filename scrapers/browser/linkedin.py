"""LinkedIn job scraper using Playwright with personal session."""
import asyncio
import random
from pathlib import Path
from typing import List, Dict

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from app_config.settings import SESSION_DIR, REQUEST_DELAY, LINKEDIN_MAX_PAGES
from scrapers.base import BaseScraper


class LinkedInScraper(BaseScraper):
    def __init__(self, keywords: str = "software engineer", location: str = "India"):
        self.keywords = keywords
        self.location = location
        self.storage_path = SESSION_DIR / "linkedin_storage.json"

    async def login_and_save(self, email: str, password: str):
        """One-time setup: login manually and save session."""
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36")
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            print("[LinkedIn] Opening login page...")
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            await page.fill("#username", email)
            await page.fill("#password", password)
            await page.click("button[type='submit']")

            print("[LinkedIn] Waiting for feed (complete 2FA if needed)...")
            await page.wait_for_url("https://www.linkedin.com/feed/*", timeout=120000)

            await context.storage_state(path=str(self.storage_path))
            print(f"[LinkedIn] Session saved to {self.storage_path}")
            await browser.close()

    async def scrape(self) -> List[Dict]:
        if not self.storage_path.exists():
            print("[LinkedIn] ERROR: No session found. Run login_and_save() first.")
            return []

        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                storage_state=str(self.storage_path),
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            encoded_kw = self.keywords.replace(" ", "%20")
            encoded_loc = self.location.replace(" ", "%20")

            for page_num in range(LINKEDIN_MAX_PAGES):
                start = page_num * 25
                url = (f"https://www.linkedin.com/jobs/search/"
                       f"?keywords={encoded_kw}&location={encoded_loc}&start={start}")

                print(f"[LinkedIn] Scraping page {page_num + 1}: {url}")
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(5)

                # Try multiple selectors since LinkedIn changes them
                selectors = [
                    "[data-job-id]",
                    ".job-card-container",
                    ".jobs-search-results__list-item"
                ]

                cards = []
                for sel in selectors:
                    cards = await page.query_selector_all(sel)
                    if cards:
                        break

                print(f"[LinkedIn] Found {len(cards)} cards")

                for card in cards:
                    try:
                        job = await self._parse_card(page, card)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        continue

                # Human-like delay
                delay = random.uniform(REQUEST_DELAY[0], REQUEST_DELAY[1])
                print(f"[LinkedIn] Sleeping {delay:.1f}s...")
                await asyncio.sleep(delay)

            await browser.close()

        print(f"[LinkedIn] Total jobs scraped: {len(jobs)}")
        return jobs

    async def _parse_card(self, page, card) -> Dict:
        """Extract data from a job card element."""
        # Extract title
        title = await card.query_selector_eval(
            ".job-card-list__title, .job-card-container__link, h3",
            "el => el.innerText"
        )

        # Extract company
        company = await card.query_selector_eval(
            ".job-card-container__company-name, .artdeco-entity-lockup__subtitle",
            "el => el.innerText"
        )

        # Extract location
        location = await card.query_selector_eval(
            ".job-card-container__metadata-item, .artdeco-entity-lockup__caption",
            "el => el.innerText"
        )

        # Extract link
        link = await card.query_selector_eval("a", "el => el.href")

        if not title or not link:
            return None

        return {
            "job_id": f"li_{hash(link) & 0xFFFFFFFF}",
            "title": title.strip()[:200],
            "company": (company or "Unknown").strip()[:100],
            "location": (location or "Remote").strip()[:100],
            "employment_type": "Unknown",
            "description": "",
            "requirements": "",
            "apply_url": link.split("?")[0],
            "source_platform": "linkedin",
            "source_url": link,
            "posted_date": ""
        }
