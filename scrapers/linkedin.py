"""LinkedIn job scraper using Playwright with personal session."""
import asyncio
import inspect
import random
from pathlib import Path
from typing import List, Dict

from playwright.async_api import async_playwright

# ── playwright-stealth compatibility ──────────────────────────────────────────
# Different versions of playwright-stealth expose the helper differently:
#   v1.x  → stealth_async(page)   (coroutine function)
#   v2.x  → Stealth()             (class whose __call__ may not be awaitable)
# We normalise everything into a single async helper: _apply_stealth(page).
# ─────────────────────────────────────────────────────────────────────────────
HAS_STEALTH = False
_stealth_fn = None

try:
    from playwright_stealth import stealth_async as _raw_stealth
    # Confirm it is actually callable and is a coroutine function
    if callable(_raw_stealth) and inspect.iscoroutinefunction(_raw_stealth):
        _stealth_fn = _raw_stealth
        HAS_STEALTH = True
    else:
        print("[LinkedIn] stealth_async found but not awaitable — trying stealth()")
except ImportError:
    pass

if not HAS_STEALTH:
    try:
        from playwright_stealth import stealth as _raw_stealth
        if callable(_raw_stealth) and inspect.iscoroutinefunction(_raw_stealth):
            _stealth_fn = _raw_stealth
            HAS_STEALTH = True
    except ImportError:
        pass

if not HAS_STEALTH:
    # Last resort: try the v2 Stealth class — it is used as an async context manager
    # on the browser context, NOT called directly on the page.
    try:
        from playwright_stealth import Stealth as _StealthClass   # noqa: F401
        HAS_STEALTH = True          # flag only; actual usage is in _stealth_context()
    except Exception:
        print("[LinkedIn] Warning: playwright-stealth not available or incompatible")


async def _apply_stealth(page):
    """Safe wrapper — calls stealth only when available and actually callable."""
    if not HAS_STEALTH or _stealth_fn is None:
        return
    try:
        result = _stealth_fn(page)
        if inspect.isawaitable(result):
            await result
    except Exception as e:
        print(f"[LinkedIn] Stealth apply failed (non-fatal): {e}")


def _stealth_context(playwright_instance):
    """
    Return an async context manager that wraps browser launch with stealth (v2),
    or a plain null context manager when stealth is unavailable / v1 style.

    v2 usage:  async with Stealth().use_async(playwright) as browser: ...
    v1 usage:  stealth is applied per-page via _apply_stealth(); no context needed.
    """
    import contextlib

    @contextlib.asynccontextmanager
    async def _null_ctx(p):
        yield None

    if not HAS_STEALTH or _stealth_fn is not None:
        # v1 path: stealth applied per-page; nothing to do at browser level
        return _null_ctx(playwright_instance)

    try:
        from playwright_stealth import Stealth as _StealthClass
        return _StealthClass().use_async(playwright_instance)
    except Exception:
        return _null_ctx(playwright_instance)


# ─────────────────────────────────────────────────────────────────────────────

from app_config.settings import SESSION_DIR, REQUEST_DELAY, LINKEDIN_MAX_PAGES
from scrapers.base import BaseScraper


class LinkedInScraper(BaseScraper):
    def __init__(self, keywords: str = "software engineer", location: str = "India"):
        self.keywords = keywords
        self.location = location
        self.storage_path = SESSION_DIR / "linkedin_storage.json"

    async def login_and_save(self, email: str, password: str):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            # v2 stealth: browser launched inside Stealth().use_async(p) context.
            # v1 stealth: plain browser launch; stealth applied per-page below.
            _sc = _stealth_context(p)
            stealth_browser = None
            try:
                stealth_browser = await _sc.__aenter__()
            except Exception:
                pass

            if stealth_browser is not None:
                browser = stealth_browser
                print("[LinkedIn] Stealth v2 active (browser-level)")
            else:
                browser = await p.chromium.launch(headless=False)

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            await _apply_stealth(page)          # v1 per-page stealth (no-op for v2)

            print("[LinkedIn] Opening login page...")
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

            # Give the page extra time to fully render and dismiss any overlays
            await asyncio.sleep(4)

            # ── Dismiss cookie / GDPR consent banner if present ───────────────
            for consent_sel in [
                "button[action-type='ACCEPT']",
                "button[data-tracking-control-name='public_jobs_join-login-modal_accept-cookies']",
                "button.artdeco-global-alert-action--primary",
                "#artdeco-global-alert-container button",
            ]:
                try:
                    btn = await page.query_selector(consent_sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        print(f"[LinkedIn] Dismissed consent banner ({consent_sel})")
                        await asyncio.sleep(2)
                        break
                except Exception:
                    pass

            # ── Debug: save screenshot so you can see what loaded ─────────────
            screenshot_path = str(SESSION_DIR / "linkedin_debug.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"[LinkedIn] Screenshot saved → {screenshot_path}")
            print(f"[LinkedIn] Current URL: {page.url}")

            # ── Wait for login form (extended timeout for slow connections) ────
            try:
                await page.wait_for_selector(
                    "#username, input[name='session_key']", timeout=30000
                )
            except Exception:
                # Form not found — the browser window is open.
                # This can happen if LinkedIn shows a CAPTCHA or checkpoint.
                # Wait up to 3 minutes for the user to solve it manually.
                print("[LinkedIn] ⚠️  Login form not detected automatically.")
                print("[LinkedIn] → Please complete the login manually in the browser window.")
                print("[LinkedIn] → The script will wait up to 3 minutes for you to reach the feed.")
                await page.wait_for_url("https://www.linkedin.com/feed/*", timeout=180000)
                await context.storage_state(path=str(self.storage_path))
                print(f"[LinkedIn] Session saved to {self.storage_path}")
                await browser.close()
                return

            if await page.query_selector("#username"):
                print("[LinkedIn] Using modern login form (#username / #password)")
                await page.fill("#username", email)
                await page.fill("#password", password)
                await page.click("button[type='submit']")
            else:
                print("[LinkedIn] Using legacy login form (session_key / session_password)")
                await page.fill("input[name='session_key']", email)
                await page.fill("input[name='session_password']", password)
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
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            await _apply_stealth(page)          # ← safe wrapper

            encoded_kw  = self.keywords.replace(" ", "%20")
            encoded_loc = self.location.replace(" ", "%20")

            for page_num in range(LINKEDIN_MAX_PAGES):
                start = page_num * 25
                url = (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={encoded_kw}&location={encoded_loc}&start={start}"
                )

                print(f"[LinkedIn] Scraping page {page_num + 1}: {url}")

                try:
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                except Exception:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                await asyncio.sleep(5)  # let JS render

                jobs_found = await self._extract_jobs(page)

                if not jobs_found:
                    print(f"[LinkedIn] No jobs on page {page_num + 1}, trying scroll...")
                    for _ in range(3):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)
                        jobs_found = await self._extract_jobs(page)
                        if jobs_found:
                            break

                print(f"[LinkedIn] Found {len(jobs_found)} jobs on page {page_num + 1}")
                jobs.extend(jobs_found)

                delay = random.uniform(REQUEST_DELAY[0], REQUEST_DELAY[1])
                print(f"[LinkedIn] Sleeping {delay:.1f}s...")
                await asyncio.sleep(delay)

            await browser.close()

        print(f"[LinkedIn] Total jobs scraped: {len(jobs)}")
        return jobs

    async def _extract_jobs(self, page) -> List[Dict]:
        """Extract jobs using multiple selector strategies."""
        selectors = [
            ".job-card-container",
            ".jobs-search-results__list-item",
            "[data-job-id]",
            "li[data-occludable-job-id]",
            ".artdeco-entity-lockup",
        ]

        cards = []
        for selector in selectors:
            cards = await page.query_selector_all(selector)
            if cards:
                print(f"[LinkedIn] Using selector: {selector} ({len(cards)} cards)")
                break

        if not cards:
            cards = await page.query_selector_all("//li[contains(@class, 'job')]")
            if cards:
                print(f"[LinkedIn] Using XPath fallback ({len(cards)} cards)")

        jobs = []
        for card in cards:
            try:
                job = await self._parse_card(page, card)
                if job:
                    jobs.append(job)
            except Exception:
                continue

        return jobs

    async def _parse_card(self, page, card) -> Dict:
        """Parse a single job card with multiple field selectors."""

        title = await self._try_selectors(card, [
            ".job-card-list__title",
            ".job-card-container__link",
            "h3",
            "a.job-card-list__title",
            "[data-control-name='job_title']",
            "strong",
        ])

        company = await self._try_selectors(card, [
            ".job-card-container__company-name",
            ".artdeco-entity-lockup__subtitle",
            ".company-name",
            "[data-control-name='company']",
        ])

        location = await self._try_selectors(card, [
            ".job-card-container__metadata-item",
            ".artdeco-entity-lockup__caption",
            ".location",
            "[data-control-name='location']",
        ])

        link = await self._try_selectors(card, [
            "a.job-card-list__title",
            "a.job-card-container__link",
            "a[href*='/jobs/view/']",
            "a",
        ], attr="href")

        if not title or not link:
            return None

        if link and not link.startswith("http"):
            link = f"https://www.linkedin.com{link}"

        return {
            "job_id":           f"li_{hash(link) & 0xFFFFFFFF}",
            "title":            title.strip()[:200],
            "company":          (company or "Unknown").strip()[:100],
            "location":         (location or "Remote").strip()[:100],
            "employment_type":  "Unknown",
            "description":      "",
            "requirements":     "",
            "apply_url":        link.split("?")[0] if link else "",
            "source_platform":  "linkedin",
            "source_url":       link or "",
            "posted_date":      "",
        }

    async def _try_selectors(self, element, selectors, attr=None):
        """Try multiple selectors and return the first non-empty match."""
        for selector in selectors:
            try:
                el = await element.query_selector(selector)
                if el:
                    if attr:
                        return await el.get_attribute(attr)
                    text = await el.text_content()
                    if text and text.strip():
                        return text.strip()
            except Exception:
                continue
        return ""