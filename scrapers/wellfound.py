"""Wellfound (AngelList) scraper using their API."""
import asyncio
import httpx
from typing import List, Dict


class WellfoundScraper:
    """Scrape Wellfound jobs via their public API."""

    API_URL = "https://wellfound.com/jobs"

    async def scrape(self) -> List[Dict]:
        jobs = []

        # Wellfound roles to search
        roles = ["software-engineer", "backend-engineer", "full-stack-engineer", 
                 "frontend-engineer", "devops-engineer", "data-engineer"]

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
            }

            for role in roles:
                try:
                    page = 1
                    while page <= 3:  # Max 3 pages per role
                        url = f"{self.API_URL}/{role}?page={page}"
                        print(f"   [Wellfound] Fetching {role} page {page}...", end=" ")

                        resp = await client.get(url, headers=headers)
                        if resp.status_code != 200:
                            print(f"status {resp.status_code}")
                            break

                        # Parse HTML for job listings
                        from selectolax.parser import HTMLParser
                        tree = HTMLParser(resp.text)

                        page_jobs = []

                        # Try multiple selectors
                        selectors = [
                            "[data-test='startup-job-listing']",
                            ".styles_jobListing__",
                            ".job-listing",
                            "[data-test='job-listing']",
                            ".styles-module_component__",
                        ]

                        for sel in selectors:
                            cards = tree.css(sel)
                            if cards:
                                for card in cards:
                                    try:
                                        title_el = card.css_first("h2, h3, .title, [data-test='job-title']")
                                        company_el = card.css_first(".company-name, [data-test='company-name'], .startup-name")
                                        loc_el = card.css_first(".location, [data-test='location']")
                                        link_el = card.css_first("a[href^='/jobs/'], a[href^='/company/']")

                                        if not title_el:
                                            continue

                                        title = title_el.text(strip=True)
                                        company = company_el.text(strip=True) if company_el else "Unknown"
                                        location = loc_el.text(strip=True) if loc_el else "Remote"

                                        href = ""
                                        if link_el:
                                            href = link_el.attributes.get("href", "")
                                            if not href.startswith("http"):
                                                href = f"https://wellfound.com{href}"

                                        page_jobs.append({
                                            "job_id": f"wf_{hash(title + company) & 0xFFFFFFFF}",
                                            "title": title[:200],
                                            "company": company[:100],
                                            "location": location[:100],
                                            "employment_type": "Full-time",
                                            "description": "",
                                            "requirements": "",
                                            "apply_url": href,
                                            "source_platform": "wellfound",
                                            "source_url": url,
                                            "posted_date": ""
                                        })
                                    except:
                                        continue
                                break

                        # Also try regex fallback
                        if not page_jobs:
                            import re
                            # Look for job data in script tags (Next.js data)
                            scripts = tree.css("script")
                            for script in scripts:
                                text = script.text()
                                if "job" in text.lower() and "title" in text.lower():
                                    # Try to extract JSON data
                                    try:
                                        matches = re.findall(r'"title":"([^"]+)".*?"companyName":"([^"]+)"', text)
                                        for title, company in matches[:10]:
                                            page_jobs.append({
                                                "job_id": f"wf_{hash(title + company) & 0xFFFFFFFF}",
                                                "title": title[:200],
                                                "company": company[:100],
                                                "location": "Remote",
                                                "employment_type": "Full-time",
                                                "apply_url": "",
                                                "source_platform": "wellfound",
                                                "source_url": url,
                                                "posted_date": ""
                                            })
                                    except:
                                        pass

                        print(f"{len(page_jobs)} jobs")
                        jobs.extend(page_jobs)

                        if len(page_jobs) < 5:
                            break

                        page += 1
                        await asyncio.sleep(2)

                except Exception as e:
                    print(f"ERROR: {e}")

        return jobs
