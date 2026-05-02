"""Universal job scraper — aggregates from multiple sources."""
import asyncio
from typing import List, Dict

from scrapers.hackernews import HNScraper
from scrapers.wellfound import WellfoundScraper
from scrapers.remoteok import RemoteOKScraper
from scrapers.github_jobs import GitHubJobsScraper


class UniversalJobScraper:
    """Scrape jobs from multiple aggregators."""

    async def scrape_all(self) -> List[Dict]:
        all_jobs = []

        # 1. Hacker News
        print("\n[1/4] Scraping Hacker News...")
        try:
            hn = HNScraper()
            jobs = await hn.scrape()
            all_jobs.extend(jobs)
            print(f"   Got {len(jobs)} jobs")
        except Exception as e:
            print(f"   ERROR: {e}")

        # 2. Wellfound
        # print("\n[2/4] Scraping Wellfound...")
        # try:
        #     wf = WellfoundScraper()
        #     jobs = await wf.scrape()
        #     all_jobs.extend(jobs)
        #     print(f"   Got {len(jobs)} jobs")
        # except Exception as e:
        #     print(f"   ERROR: {e}")

        # 3. RemoteOK
        print("\n[3/4] Scraping RemoteOK...")
        try:
            ro = RemoteOKScraper()
            jobs = await ro.scrape()
            all_jobs.extend(jobs)
            print(f"   Got {len(jobs)} jobs")
        except Exception as e:
            print(f"   ERROR: {e}")

        # 4. GitHub
        print("\n[4/4] Scraping GitHub curated lists...")
        try:
            gh = GitHubJobsScraper()
            jobs = await gh.scrape()
            all_jobs.extend(jobs)
            print(f"   Got {len(jobs)} jobs")
        except Exception as e:
            print(f"   ERROR: {e}")

        return all_jobs
