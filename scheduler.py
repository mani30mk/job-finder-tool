"""Job Scraper — runs a single scrape cycle.

Used by:
  - GitHub Actions daily cron (`.github/workflows/daily-scraper.yml`)
  - Manual local runs: `python scheduler.py --run-once`

Usage:
    python scheduler.py --run-once       # Run once and exit (CI/CD mode)
    python scheduler.py                  # Same as --run-once
"""
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# ── Logging setup ──────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "scraper.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("scheduler")


def run_scrape_cycle():
    """Execute a full scrape cycle: scrape → deduplicate → insert → cleanup."""
    log.info("=" * 60)
    log.info("Starting scrape cycle at %s", datetime.now().isoformat())
    log.info("=" * 60)

    try:
        import asyncio
        from app_config.config import Config
        from database.db import init_db, insert_jobs, get_stats, get_existing_job_ids, deactivate_old_jobs
        from parser.normalizer import normalize_job
        from parser.dedup import Deduplicator

        Config.load()
        init_db()

        existing = get_existing_job_ids()
        seen = set(existing)
        all_jobs = []

        # ── Phase 1: Universal aggregators (HN, RemoteOK, GitHub) ──
        log.info("Phase 1: Universal aggregators")
        try:
            from scrapers.universal import UniversalJobScraper
            uni = UniversalJobScraper()
            jobs = asyncio.run(uni.scrape_all())
            all_jobs.extend(jobs)
            log.info("  Universal: %d jobs", len(jobs))
        except Exception as e:
            log.error("  Universal ERROR: %s", e)

        # ── Phase 2: Triple API (SerpApi → JSearch → TheirStack) ──
        log.info("Phase 2: Google Jobs (3-API fallback)")
        try:
            from scrapers.triple_google_jobs import TripleGoogleJobsScraper
            triple = TripleGoogleJobsScraper(
                serpapi_key=Config.SERPAPI_KEY,
                jsearch_key=Config.RAPIDAPI_KEY,
                theirstack_key=Config.THEIRSTACK_KEY,
                query=Config.DEFAULT_QUERY,
                location=Config.DEFAULT_LOCATION,
                num_results=50,
            )
            jobs = asyncio.run(triple.scrape())
            all_jobs.extend(jobs)
            log.info("  Triple API: %d jobs", len(jobs))
        except ImportError:
            log.info("  Triple API scraper not available")
        except Exception as e:
            log.error("  Triple API ERROR: %s", e)

        # ── Phase 3: Additional API aggregators ──
        log.info("Phase 3: Additional aggregators")
        try:
            from scrapers.jobicy import JobicyScraper
            jc = JobicyScraper(count=50)
            jobs = asyncio.run(jc.scrape())
            all_jobs.extend(jobs)
            log.info("  Jobicy: %d jobs", len(jobs))
        except ImportError:
            pass
        except Exception as e:
            log.error("  Jobicy ERROR: %s", e)

        try:
            from scrapers.adzuna import AdzunaScraper
            if Config.has_key("ADZUNA_APP_KEY"):
                adz = AdzunaScraper(
                    app_id=Config.ADZUNA_APP_ID,
                    app_key=Config.ADZUNA_APP_KEY,
                    country=Config.DEFAULT_COUNTRY,
                    query=Config.DEFAULT_QUERY,
                    max_results=20,
                )
                jobs = asyncio.run(adz.scrape())
                all_jobs.extend(jobs)
                log.info("  Adzuna: %d jobs", len(jobs))
        except ImportError:
            pass
        except Exception as e:
            log.error("  Adzuna ERROR: %s", e)

        # ── Phase 4: Internshala (India-specific internships) — TOP PRIORITY ──
        log.info("Phase 4: Internshala (India internships)")
        try:
            from scrapers.html.internshala import InternshalaScraper
            ins = InternshalaScraper()
            jobs = asyncio.run(ins.scrape())
            all_jobs.extend(jobs)
            log.info("  Internshala: %d jobs", len(jobs))
        except Exception as e:
            log.error("  Internshala ERROR: %s", e)

        # ── Phase 5: Free API sources (Remotive + Arbeitnow) ──
        log.info("Phase 5: Free API sources (Remotive + Arbeitnow)")
        try:
            from scrapers.remotive_api import RemotiveScraper
            remotive_jobs = asyncio.run(RemotiveScraper(limit=200).scrape())
            all_jobs.extend(remotive_jobs)
            log.info("  Remotive: %d jobs", len(remotive_jobs))
        except Exception as e:
            log.error("  Remotive ERROR: %s", e)

        try:
            from scrapers.arbeitnow_api import ArbeitnowScraper
            arbeitnow_jobs = asyncio.run(ArbeitnowScraper(max_pages=3).scrape())
            all_jobs.extend(arbeitnow_jobs)
            log.info("  Arbeitnow: %d jobs", len(arbeitnow_jobs))
        except Exception as e:
            log.error("  Arbeitnow ERROR: %s", e)

        # ── Phase 6: India-specific HTML scrapers ──
        log.info("Phase 6: India-specific (Naukri + Freshersworld)")
        try:
            from scrapers.naukri import NaukriScraper
            naukri_jobs = asyncio.run(NaukriScraper(delay=3.0).scrape())
            all_jobs.extend(naukri_jobs)
            log.info("  Naukri: %d jobs", len(naukri_jobs))
        except Exception as e:
            log.error("  Naukri ERROR: %s", e)

        try:
            from scrapers.html.freshersworld import FreshersworldScraper
            fw_jobs = asyncio.run(FreshersworldScraper().scrape())
            all_jobs.extend(fw_jobs)
            log.info("  Freshersworld: %d jobs", len(fw_jobs))
        except Exception as e:
            log.error("  Freshersworld ERROR: %s", e)

        # ── Deduplicate and insert ──
        log.info("Processing %d total scraped jobs...", len(all_jobs))
        unique_jobs = []
        for job in all_jobs:
            normalized = normalize_job(job)
            dup_id = Deduplicator.generate_id(normalized)
            if dup_id not in seen:
                seen.add(dup_id)
                unique_jobs.append(normalized)

        inserted = insert_jobs(unique_jobs)

        # ── Cleanup: deactivate old jobs ──
        deactivate_old_jobs(days=14)
        log.info("Deactivated jobs older than 14 days")

        # ── Summary ──
        stats = get_stats()
        log.info("-" * 40)
        log.info("Inserted: %d new jobs", inserted)
        log.info("Skipped:  %d duplicates", len(all_jobs) - len(unique_jobs))
        log.info("Database: %d total | %d active", stats["total"], stats["active"])

        # ── Gemini semantic scoring of new jobs ──
        log.info("Running Gemini semantic scoring...")
        try:
            from recommendation.gemini_scorer import score_new_jobs
            scored = asyncio.run(score_new_jobs(limit=100))
            log.info("Gemini scored %d jobs", scored)
        except Exception as e:
            log.warning("Gemini scoring failed (non-fatal): %s", e)

        log.info("Cycle completed at %s", datetime.now().isoformat())
        log.info("=" * 60)

        return inserted

    except Exception as e:
        log.exception("Scrape cycle FAILED: %s", e)
        return -1


def main():
    parser = argparse.ArgumentParser(
        description="Job Hunter — Daily Scraper (for GitHub Actions / CI)",
    )
    parser.add_argument(
        "--run-once", action="store_true", default=True,
        help="Run a single scrape cycle and exit (default behavior)",
    )
    args = parser.parse_args()

    result = run_scrape_cycle()
    sys.exit(0 if result >= 0 else 1)


if __name__ == "__main__":
    main()
