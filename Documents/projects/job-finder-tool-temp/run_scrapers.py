"""Main orchestrator — uses universal scraper + existing sources."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import asyncio
from app_config.config import Config
from database.db import init_db, insert_jobs, get_stats, get_existing_job_ids
from parser.normalizer import normalize_job
from parser.dedup import Deduplicator
from scrapers.universal import UniversalJobScraper
from scrapers.html.internshala import InternshalaScraper

# Load configuration from .env file
Config.load()

# Optional: API-based sources (all deployable, no browser)
try:
    from scrapers.triple_google_jobs import TripleGoogleJobsScraper
    HAS_TRIPLE_API = True
except ImportError:
    HAS_TRIPLE_API = False

try:
    from scrapers.jobicy import JobicyScraper
    HAS_JOBICY = True
except ImportError:
    HAS_JOBICY = False

try:
    from scrapers.adzuna import AdzunaScraper
    HAS_ADZUNA = True
except ImportError:
    HAS_ADZUNA = False


async def run_all():
    print("=" * 50)
    print("Job Hunter — Universal Scraper")
    print("=" * 50)

    init_db()
    existing = get_existing_job_ids()
    seen = set(existing)
    all_jobs = []

    # 1. Universal scraper (HN + RemoteOK + GitHub)
    print("\n--- Phase 1: Universal Aggregators ---")
    uni = UniversalJobScraper()
    jobs = await uni.scrape_all()
    all_jobs.extend(jobs)

    # 2. Triple API: SerpApi + JSearch + TheirStack (auto-fallback)
    print("\n--- Phase 2: Google Jobs (3-API Fallback) ---")
    print("   Priority: SerpApi -> JSearch -> TheirStack")
    print("   Auto-switches if API quota exceeded")

    if HAS_TRIPLE_API:
        try:
            triple = TripleGoogleJobsScraper(
                serpapi_key=Config.SERPAPI_KEY,
                jsearch_key=Config.RAPIDAPI_KEY,
                theirstack_key=Config.THEIRSTACK_KEY,
                query=Config.DEFAULT_QUERY,
                location=Config.DEFAULT_LOCATION,
                num_results=50,
            )
            jobs = await triple.scrape()
            all_jobs.extend(jobs)
            print(f"   Got {len(jobs)} jobs from triple API")
        except Exception as e:
            print(f"   ERROR: {e}")
    else:
        print("   Triple API scraper not found")

    # 3. Additional API aggregators
    print("\n--- Phase 3: Additional API Aggregators ---")

    if HAS_JOBICY:
        try:
            jc = JobicyScraper(count=50)
            jobs = await jc.scrape()
            all_jobs.extend(jobs)
            print(f"   Jobicy: {len(jobs)} jobs")
        except Exception as e:
            print(f"   Jobicy ERROR: {e}")

    if HAS_ADZUNA and Config.has_key("ADZUNA_APP_KEY"):
        try:
            adz = AdzunaScraper(
                app_id=Config.ADZUNA_APP_ID,
                app_key=Config.ADZUNA_APP_KEY,
                country=Config.DEFAULT_COUNTRY,
                query=Config.DEFAULT_QUERY,
                max_results=20,
            )
            jobs = await adz.scrape()
            all_jobs.extend(jobs)
            print(f"   Adzuna: {len(jobs)} jobs")
        except Exception as e:
            print(f"   Adzuna ERROR: {e}")

    # 4. Internshala (India-specific)
    print("\n--- Phase 4: Internshala ---")
    try:
        ins = InternshalaScraper()
        jobs = await ins.scrape()
        all_jobs.extend(jobs)
        print(f"   Got {len(jobs)} jobs")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Deduplicate and insert
    print("\n--- Processing ---")
    unique_jobs = []
    for job in all_jobs:
        normalized = normalize_job(job)
        dup_id = Deduplicator.generate_id(normalized)
        if dup_id not in seen:
            seen.add(dup_id)
            unique_jobs.append(normalized)

    inserted = insert_jobs(unique_jobs)

    print(f"\n{'=' * 50}")
    print(f"Inserted {inserted} new jobs")
    print(f"Skipped {len(all_jobs) - len(unique_jobs)} duplicates")

    stats = get_stats()
    print(f"\nDatabase: {stats['total']} total | {stats['active']} active")
    print(f"\nRun `python -m interface.cli` to search")


if __name__ == "__main__":
    asyncio.run(run_all())