# CLAUDE.md — Job Hunter Improvement Implementation Guide

> **For:** Claude Opus 4.6 (agentic / Claude Code mode)  
> **Project root:** `C:\Users\manio\Documents\projects\previous\job-hunter\`  
> **Goal:** Implement all improvements from the proposal. Zero manual steps for the developer.  
> **Constraint:** Everything must be free. No paid APIs.

---

## BEFORE YOU START — Read This Fully First

### Project Structure (what exists)
```
job-hunter/
├── api/
│   └── main.py                  ← FastAPI backend (modify)
├── app_config/
│   ├── config.py                ← API key loader
│   └── settings.py              ← Keywords/locations (MODIFY FIRST)
├── alerts/
│   └── telegram.py              ← Telegram notifier (modify)
├── database/
│   ├── db.py                    ← SQLite helpers (modify)
│   └── models.py                ← Schema
├── parser/
│   └── dedup.py                 ← Deduplication (modify)
├── recommendation/
│   ├── engine.py                ← Keyword scorer (keep, add Gemini alongside)
│   └── gemini_scorer.py         ← CREATE THIS (Gemini semantic scoring)
├── scrapers/
│   ├── remotive_api.py          ← CREATE THIS
│   ├── arbeitnow_api.py         ← CREATE THIS
│   ├── naukri.py                ← CREATE THIS
│   ├── html/
│   │   ├── internshala.py       ← EXISTS (reference for style)
│   │   └── freshersworld.py     ← CREATE THIS
│   └── feeds/
│       ├── greenhouse.py        ← EXISTS
│       ├── lever.py             ← EXISTS
│       └── ashby.py             ← EXISTS
├── frontend-integrated/         ← Next.js app (modify api.ts)
├── run_scrapers.py              ← Main scraper runner (modify)
├── scheduler.py                 ← Daily pipeline (modify)
├── .env                         ← Add GEMINI_API_KEY here
└── jobs.db                      ← SQLite DB (run migrations)
```

### Tech Stack
- **Backend:** Python 3.10+, FastAPI, SQLite, httpx, selectolax
- **Frontend:** Next.js 15, TypeScript, Tailwind
- **Scraping style:** async httpx + selectolax (HTML), direct httpx GET (JSON APIs)
- **New dependency:** `google-generativeai` or raw httpx to Gemini REST API

### Rules
1. **Never break existing functionality.** All existing scrapers must still work.
2. **All new scrapers follow the same async pattern** as `scrapers/html/internshala.py`.
3. **Test each step** with the verification command before moving to the next.
4. **Use `httpx.AsyncClient`** everywhere, never `requests`.
5. **Gemini scoring is additive** — it writes to a new column `gemini_score`, it does NOT replace `match_score`.

---

## STEP 0 — Install Dependencies

```bash
cd C:\Users\manio\Documents\projects\previous\job-hunter
pip install rapidfuzz google-generativeai schedule httpx selectolax
```

Verify:
```bash
python -c "import rapidfuzz; import httpx; import selectolax; print('OK')"
```

---

## STEP 1 — Fix Settings (Highest Impact, Do First)

**File:** `app_config/settings.py`  
**Action:** Replace KEYWORDS, LOCATIONS, JOB_TYPES entirely.

```python
"""Global configuration for job-hunter."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "jobs.db"
SESSION_DIR = BASE_DIR / "session_data"
LOGS_DIR = BASE_DIR / "logs"

# ─── Search preferences — tuned for India fresher/intern ──────────────────────
KEYWORDS = [
    # ML/AI internships (your core strength)
    "machine learning intern",
    "deep learning intern",
    "ai intern",
    "data science intern",
    "computer vision intern",
    "nlp intern",
    "ml research intern",
    "ai research intern",
    "research intern machine learning",
    # Software internships
    "software engineer intern",
    "sde intern",
    "software developer intern",
    "backend intern",
    "python intern",
    "developer intern",
    "software trainee",
    # Entry level / fresher
    "fresher software engineer",
    "junior ml engineer",
    "graduate engineer trainee",
    "associate software engineer",
    "entry level python",
    "campus hiring",
    "off campus hiring",
]

LOCATIONS = [
    "India",
    "Remote",
    "Work from home",
    "WFH",
    "Bangalore",
    "Bengaluru",
    "Chennai",
    "Hyderabad",
    "Mumbai",
    "Pune",
    "Delhi",
    "Noida",
    "Gurugram",
    "Gurgaon",
    "Tamil Nadu",
    "Karnataka",
    "Telangana",
]

JOB_TYPES = ["Internship", "Full-time", "Entry Level", "Fresher"]

# Scraping limits
LINKEDIN_MAX_PAGES = 3
WORKDAY_MAX_JOBS = 50
REQUEST_DELAY = (8, 15)

# Alerts
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")

# Ollama config
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "mistral"
```

**Verify:** `python -c "from app_config.settings import KEYWORDS; print(f'{len(KEYWORDS)} keywords loaded')"`  
Expected: `22 keywords loaded`

---

## STEP 2 — DB Migration (Add Gemini Columns)

**File:** Create `database/migrate.py`

```python
"""
Run once to add Gemini scoring columns to existing DB.
Safe to run multiple times (uses IF NOT EXISTS pattern).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "jobs.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("gemini_score",   "REAL DEFAULT 0"),
        ("gemini_reasons", "TEXT DEFAULT '[]'"),
        ("gemini_summary", "TEXT DEFAULT ''"),
    ]

    for col_name, col_def in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")
            print(f"  Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  Column already exists: {col_name}")
            else:
                raise

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
```

**Run:** `python database/migrate.py`  
**Verify:** `python -c "import sqlite3; conn=sqlite3.connect('jobs.db'); print([c[1] for c in conn.execute('PRAGMA table_info(jobs)').fetchall()])"`  
Expected output includes `gemini_score`, `gemini_reasons`, `gemini_summary`.

---

## STEP 3 — Gemini Semantic Scorer

**File:** Create `recommendation/gemini_scorer.py`

```python
"""
Gemini-powered semantic job scorer.
Model: gemini-2.5-flash-lite (free tier: 1000 req/day, 30 RPM)
Only scores jobs with is_new=1 after each daily scrape.
Writes gemini_score (0.0–1.0) to DB.
"""
import os
import json
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Use Flash-Lite for maximum free quota (1000 RPD)
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# ── Candidate profile (hardcoded — personal tool) ────────────────────────────
MY_PROFILE = """
Name: Manikandan S
Education: B.Tech Computer Science Engineering, SASTRA University (Final/Pre-Final Year)
Skills: Python, PyTorch, TensorFlow, Scikit-learn, FastAPI, SQLite, C++,
        Machine Learning, Deep Learning, Knowledge Distillation,
        Computer Vision, NLP, Competitive Programming, Data Structures & Algorithms
Projects:
  - Knowledge distillation for lung cancer classification (LC25000 dataset,
    teacher: ResNet50+InceptionV3+DenseNet121, student: MobileNetV2, TensorFlow/Keras)
  - Async Python job aggregator (scrapers: LinkedIn, Greenhouse, Lever, Internshala,
    HackerNews, GitHub; storage: SQLite FTS5; UI: FastAPI + Next.js PWA)
  - TNASSE neural architecture search paper animation (HTML5 canvas, cinematic)
Experience: 0 years (fresher / active researcher)
Target roles: ML Engineer Intern, SDE Intern, Data Science Intern,
              Research Intern, Backend Engineer Intern, AI Engineer Intern
Location preference: India (any city), Remote, Work from home
Employment types: Internship preferred, Entry-level Full-time acceptable
"""

SCORE_PROMPT = """You are an expert job-fit evaluator for a fresher candidate.

CANDIDATE PROFILE:
{profile}

JOB TO EVALUATE:
Title: {title}
Company: {company}
Location: {location}
Type: {employment_type}
Description (first 1500 chars):
{description}

TASK: Score how well this job fits this candidate. Be realistic and precise.

SCORING RULES:
- 0.85–1.00: Exceptional fit — ML/AI/SDE intern in India or Remote, skills match 80%+
- 0.70–0.85: Strong fit — related tech role, India/Remote, skills match 60%+
- 0.50–0.70: Good fit — tech role, acceptable location, some skills match
- 0.30–0.50: Weak fit — different domain but transferable skills
- 0.00–0.30: Poor fit — unrelated, requires years of experience, wrong field

PENALIZE (reduce score by 0.2):
- Role requires 3+ years experience for a fresher
- US/Europe only, no remote option, not India
- Requires domain expertise (finance, medical) with no ML angle

BOOST (increase score by 0.1):
- Explicitly says "fresher welcome" or "0-1 years"
- Internship explicitly for India
- Mentions SASTRA, IIT, NIT (campus hiring)
- ML/AI with Python/PyTorch

Respond ONLY in valid JSON. No markdown, no explanation:
{{
  "score": <float 0.0-1.0>,
  "reasons": ["<reason 1 max 10 words>", "<reason 2>", "<reason 3>"],
  "missing_skills": ["<skill1>", "<skill2>"],
  "summary": "<one sentence, max 20 words, why fit or not>"
}}"""


async def _call_gemini(prompt: str, client: httpx.AsyncClient) -> dict:
    """Make one Gemini API call. Returns parsed JSON or raises."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 350,
            "responseMimeType": "application/json",
        },
    }
    resp = await client.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    # Strip any accidental markdown fences
    text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    return json.loads(text)


async def score_job(job: Dict, client: httpx.AsyncClient) -> Dict:
    """Score one job. Returns job dict with gemini_* fields added."""
    prompt = SCORE_PROMPT.format(
        profile=MY_PROFILE,
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        employment_type=job.get("employment_type", ""),
        description=(job.get("description") or "")[:1500],
    )
    try:
        result = await _call_gemini(prompt, client)
        return {
            **job,
            "gemini_score":   float(result.get("score", 0.0)),
            "gemini_reasons": json.dumps(result.get("reasons", [])),
            "gemini_summary": result.get("summary", ""),
        }
    except Exception as e:
        print(f"   [Gemini] Failed '{job.get('title', '?')}': {type(e).__name__}: {e}")
        return {**job, "gemini_score": 0.0, "gemini_reasons": "[]", "gemini_summary": ""}


async def score_new_jobs(limit: int = 100) -> int:
    """
    Score today's new jobs (is_new=1) that have not been Gemini-scored yet.
    Called from scheduler.py after each daily scrape.
    Rate limit: 2.1s between calls to stay under 30 RPM.
    Returns count of jobs scored.
    """
    if not GEMINI_API_KEY:
        print("   [Gemini] GEMINI_API_KEY not set in .env — skipping semantic scoring")
        print("   [Gemini] Get free key at: https://aistudio.google.com/apikey")
        return 0

    import sqlite3
    db_path = Path(__file__).resolve().parent.parent / "jobs.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT job_id, title, company, location, employment_type,
               description, match_score
        FROM jobs
        WHERE is_new = 1
          AND is_active = 1
          AND (gemini_score IS NULL OR gemini_score = 0)
        ORDER BY scraped_at DESC
        LIMIT ?
    """, (limit,)).fetchall()

    if not rows:
        print("   [Gemini] No unscored new jobs found")
        conn.close()
        return 0

    jobs = [dict(r) for r in rows]
    print(f"   [Gemini] Scoring {len(jobs)} new jobs with {GEMINI_MODEL}...")

    scored = 0
    async with httpx.AsyncClient() as client:
        for i, job in enumerate(jobs):
            result = await score_job(job, client)
            conn.execute(
                """UPDATE jobs
                   SET gemini_score=?, gemini_reasons=?, gemini_summary=?
                   WHERE job_id=?""",
                (
                    result["gemini_score"],
                    result["gemini_reasons"],
                    result["gemini_summary"],
                    job["job_id"],
                )
            )
            conn.commit()
            scored += 1
            print(f"   [Gemini] [{i+1}/{len(jobs)}] {job['title'][:40]} → {result['gemini_score']:.2f}")
            # Stay under 30 RPM free tier limit
            if i < len(jobs) - 1:
                await asyncio.sleep(2.1)

    conn.close()
    print(f"   [Gemini] Done. Scored {scored} jobs.")
    return scored


async def test_scorer():
    """Quick test — score one fake job to verify API key works."""
    test_job = {
        "job_id": "test_001",
        "title": "Machine Learning Engineer Intern",
        "company": "Google",
        "location": "Bangalore, India",
        "employment_type": "Internship",
        "description": "We are looking for ML interns with experience in PyTorch, "
                       "deep learning, computer vision. Freshers welcome. "
                       "Python required. India office.",
    }
    async with httpx.AsyncClient() as client:
        result = await score_job(test_job, client)
    print(f"Test score: {result['gemini_score']}")
    print(f"Summary: {result['gemini_summary']}")
    print(f"Reasons: {result['gemini_reasons']}")


if __name__ == "__main__":
    asyncio.run(test_scorer())
```

**Add to `.env`:**
```
GEMINI_API_KEY=your_key_from_aistudio_google_com
```

**Verify:** `python recommendation/gemini_scorer.py`  
Expected: prints a score between 0.8–1.0 for the test ML intern job.

---

## STEP 4 — Remotive API Scraper (Free, No Key)

**File:** Create `scrapers/remotive_api.py`

```python
"""
Remotive public API scraper — free, no API key required.
Returns remote tech jobs. JSON API, no scraping.
Docs: https://remotive.com/api/remote-jobs
"""
import httpx
from typing import List, Dict
from datetime import datetime


class RemotiveScraper:
    """Scrape jobs from Remotive public API."""

    BASE_URL = "https://remotive.com/api/remote-jobs"
    CATEGORIES = [
        "software-dev",
        "data",
        "devops",
        "product",
    ]

    def __init__(self, limit: int = 100):
        self.limit = limit

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        async with httpx.AsyncClient(timeout=20) as client:
            for category in self.CATEGORIES:
                try:
                    resp = await client.get(
                        self.BASE_URL,
                        params={"category": category, "limit": 50},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    jobs = data.get("jobs", [])
                    normalized = [self._normalize(j) for j in jobs]
                    all_jobs.extend(normalized)
                    print(f"   [Remotive] {category}: {len(jobs)} jobs")
                except Exception as e:
                    print(f"   [Remotive] {category} failed: {e}")

        print(f"   [Remotive] Total: {len(all_jobs)} jobs")
        return all_jobs[:self.limit]

    def _normalize(self, job: dict) -> Dict:
        return {
            "title":           job.get("title", ""),
            "company":         job.get("company_name", ""),
            "location":        job.get("candidate_required_location", "Worldwide"),
            "employment_type": job.get("job_type", "full_time").replace("_", "-"),
            "description":     job.get("description", ""),
            "requirements":    "",
            "apply_url":       job.get("url", ""),
            "source_platform": "remotive",
            "posted_date":     job.get("publication_date", datetime.now().isoformat())[:10],
            "salary":          job.get("salary", ""),
            "is_new":          1,
            "is_active":       1,
        }
```

**Verify:** `python -c "import asyncio; from scrapers.remotive_api import RemotiveScraper; jobs=asyncio.run(RemotiveScraper().scrape()); print(f'{len(jobs)} jobs')"`

---

## STEP 5 — Arbeitnow API Scraper (Free, No Key)

**File:** Create `scrapers/arbeitnow_api.py`

```python
"""
Arbeitnow public Job Board API — free, no auth, no rate limits documented.
Jobs sourced directly from ATS (Greenhouse, Lever, etc.) — high quality.
Docs: https://www.arbeitnow.com/api/job-board-api
"""
import httpx
from typing import List, Dict
from datetime import datetime


class ArbeitnowScraper:
    """Scrape jobs from Arbeitnow free public API."""

    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, max_pages: int = 3):
        self.max_pages = max_pages

    async def scrape(self) -> List[Dict]:
        all_jobs = []
        async with httpx.AsyncClient(timeout=20) as client:
            for page in range(1, self.max_pages + 1):
                try:
                    resp = await client.get(
                        self.BASE_URL,
                        params={"page": page},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    jobs = data.get("data", [])
                    if not jobs:
                        break
                    normalized = [self._normalize(j) for j in jobs]
                    all_jobs.extend(normalized)
                    print(f"   [Arbeitnow] Page {page}: {len(jobs)} jobs")
                except Exception as e:
                    print(f"   [Arbeitnow] Page {page} failed: {e}")
                    break

        print(f"   [Arbeitnow] Total: {len(all_jobs)} jobs")
        return all_jobs

    def _normalize(self, job: dict) -> Dict:
        location = "Remote" if job.get("remote") else job.get("location", "")
        return {
            "title":           job.get("title", ""),
            "company":         job.get("company_name", ""),
            "location":        location,
            "employment_type": "full-time",
            "description":     job.get("description", ""),
            "requirements":    "",
            "apply_url":       job.get("url", ""),
            "source_platform": "arbeitnow",
            "posted_date":     datetime.fromtimestamp(
                                   job.get("created_at", 0)
                               ).strftime("%Y-%m-%d") if job.get("created_at") else "",
            "salary":          "",
            "is_new":          1,
            "is_active":       1,
        }
```

**Verify:** `python -c "import asyncio; from scrapers.arbeitnow_api import ArbeitnowScraper; jobs=asyncio.run(ArbeitnowScraper().scrape()); print(f'{len(jobs)} jobs')"`

---

## STEP 6 — Naukri HTML Scraper

**File:** Create `scrapers/naukri.py`

```python
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
```

**Verify:** `python -c "import asyncio; from scrapers.naukri import NaukriScraper; jobs=asyncio.run(NaukriScraper().scrape()); print(f'{len(jobs)} Naukri jobs')"`  
Expected: 50–300 jobs. If 0, Naukri changed their HTML. Check selectors with `curl https://www.naukri.com/machine-learning-jobs-in-india | grep -o 'class="[^"]*title[^"]*"' | head -5`.

---

## STEP 7 — Freshersworld HTML Scraper

**File:** Create `scrapers/html/freshersworld.py`

```python
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
```

---

## STEP 8 — Update run_scrapers.py

**File:** `run_scrapers.py`  
**Action:** Add the 4 new scrapers to the pipeline. Find the existing run function and append:

Locate the section that calls scrapers (look for `Phase 1`, `Phase 2` etc.) and add a new phase:

```python
# Add these imports at the top of run_scrapers.py
from scrapers.remotive_api import RemotiveScraper
from scrapers.arbeitnow_api import ArbeitnowScraper
from scrapers.naukri import NaukriScraper
from scrapers.html.freshersworld import FreshersworldScraper
```

Add this new phase inside the `run_all()` async function, after existing phases:

```python
    # ── Phase 5: Free API sources ──────────────────────────────────────────────
    print("\n--- Phase 5: Free API Sources (Remotive + Arbeitnow) ---")

    print("[5a] Scraping Remotive...")
    try:
        remotive_jobs = await RemotiveScraper(limit=200).scrape()
        saved, skipped = db.save_jobs(remotive_jobs)
        print(f"    Saved {saved}, skipped {skipped}")
        total_new += saved
    except Exception as e:
        print(f"    Remotive failed: {e}")

    print("[5b] Scraping Arbeitnow...")
    try:
        arbeitnow_jobs = await ArbeitnowScraper(max_pages=3).scrape()
        saved, skipped = db.save_jobs(arbeitnow_jobs)
        print(f"    Saved {saved}, skipped {skipped}")
        total_new += saved
    except Exception as e:
        print(f"    Arbeitnow failed: {e}")

    # ── Phase 6: India-specific HTML scrapers ──────────────────────────────────
    print("\n--- Phase 6: India-Specific Sources ---")

    print("[6a] Scraping Naukri.com...")
    try:
        naukri_jobs = await NaukriScraper(delay=3.0).scrape()
        saved, skipped = db.save_jobs(naukri_jobs)
        print(f"    Saved {saved}, skipped {skipped}")
        total_new += saved
    except Exception as e:
        print(f"    Naukri failed: {e}")

    print("[6b] Scraping Freshersworld.com...")
    try:
        fw_jobs = await FreshersworldScraper().scrape()
        saved, skipped = db.save_jobs(fw_jobs)
        print(f"    Saved {saved}, skipped {skipped}")
        total_new += saved
    except Exception as e:
        print(f"    Freshersworld failed: {e}")
```

---

## STEP 9 — Update scheduler.py

**File:** `scheduler.py`  
**Action:** Add Gemini scoring step after scraping. Find the `_run_pipeline` async function and insert after `await run_all()`:

```python
    # Step 2b — Gemini semantic scoring of new jobs
    log.info("[2b/4] Running Gemini semantic scoring...")
    try:
        from recommendation.gemini_scorer import score_new_jobs
        scored = await score_new_jobs(limit=100)
        log.info(f"       Gemini scored {scored} jobs")
    except Exception as e:
        log.warning(f"       Gemini scoring failed (non-fatal): {e}")
```

---

## STEP 10 — Update API Endpoint to Use Gemini Score

**File:** `api/main.py`  
**Action:** In `get_default_recommendations()`, sort by `gemini_score` when available.

Find the line where recommendations are built and change the `_fetch_jobs` ORDER BY:

In `recommendation/engine.py`, find `_fetch_jobs` and update:

```python
cursor.execute("""
    SELECT *,
           CASE WHEN gemini_score > 0 THEN gemini_score ELSE 0 END as effective_score
    FROM jobs 
    WHERE is_active = 1 
    ORDER BY effective_score DESC, posted_date DESC
    LIMIT 500
""")
```

Also in `api/main.py` in `get_default_recommendations`, update the JobResponse to expose `gemini_score`:

Find the loop that builds `recommendations` and add:
```python
# Inside the loop building each recommendation dict
"match_score": round(
    result.get("gemini_score") or match.overall_score, 2
),
"match_reasons": result.get("gemini_reasons_list") or match.match_reasons,
"gemini_summary": result.get("gemini_summary", ""),
```

---

## STEP 11 — Fuzzy Deduplication

**File:** `parser/dedup.py`  
**Action:** Add fuzzy check using rapidfuzz. Find `is_duplicate` or the dedup class and add:

```python
# Add at top of dedup.py
try:
    from rapidfuzz import fuzz as _fuzz
    _RAPIDFUZZ_AVAILABLE = True
except ImportError:
    _RAPIDFUZZ_AVAILABLE = False


def is_fuzzy_duplicate(new_title: str, new_company: str,
                        existing_title: str, existing_company: str) -> bool:
    """
    Returns True if two jobs are likely the same posting.
    Catches variants like 'SDE Intern' vs 'Software Development Engineer Intern'.
    """
    if not _RAPIDFUZZ_AVAILABLE:
        return False
    title_sim   = _fuzz.token_sort_ratio(new_title.lower(), existing_title.lower())
    company_sim = _fuzz.ratio(new_company.lower(), existing_company.lower())
    return title_sim >= 85 and company_sim >= 88
```

---

## STEP 12 — Add GEMINI_API_KEY to .env

**File:** `.env`  
**Action:** Append this line (do not overwrite existing content):

```bash
GEMINI_API_KEY=get_from_aistudio_google_com
```

**How to get the key:**
1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key (starts with `AIza...`)
4. Replace `get_from_aistudio_google_com` in `.env`

---

## STEP 13 — Frontend: Show Gemini Summary on Job Cards

**File:** `frontend-integrated/lib/api.ts`  
**Action:** In `transformJob()`, use `gemini_score` when available and expose `gemini_summary`:

```typescript
// In transformJob() function, update matchScore line:
matchScore: typeof b.gemini_score === "number" && b.gemini_score > 0
  ? b.gemini_score
  : typeof b.match_score === "number" ? b.match_score : 0,

// Add gemini_summary to return object (add to Job type too if needed):
// description field: prepend gemini_summary if present
description: b.gemini_summary
  ? `${b.gemini_summary}\n\n${b.description || ""}`
  : b.description || "",
```

**Also update `BackendJob` interface** to include:
```typescript
gemini_score?: number;
gemini_summary?: string;
gemini_reasons?: string[];
```

---

## FINAL VERIFICATION

Run these in order:

```bash
# 1. Test settings
python -c "from app_config.settings import KEYWORDS, LOCATIONS; print(f'{len(KEYWORDS)} keywords, {len(LOCATIONS)} locations')"

# 2. Test DB migration
python database/migrate.py

# 3. Test Gemini scorer (need API key in .env first)
python recommendation/gemini_scorer.py

# 4. Test Remotive
python -c "import asyncio; from scrapers.remotive_api import RemotiveScraper; print(asyncio.run(RemotiveScraper().scrape())[0]['title'])"

# 5. Test Arbeitnow
python -c "import asyncio; from scrapers.arbeitnow_api import ArbeitnowScraper; print(asyncio.run(ArbeitnowScraper().scrape())[0]['title'])"

# 6. Test Naukri
python -c "import asyncio; from scrapers.naukri import NaukriScraper; jobs=asyncio.run(NaukriScraper().scrape()); print(f'{len(jobs)} Naukri jobs')"

# 7. Full scraper run
python run_scrapers.py

# 8. Check DB counts by source
python -c "
import sqlite3
conn = sqlite3.connect('jobs.db')
rows = conn.execute('SELECT source_platform, COUNT(*) FROM jobs WHERE is_active=1 GROUP BY source_platform ORDER BY 2 DESC').fetchall()
for r in rows: print(f'  {r[0]:<20} {r[1]}')
"

# 9. Start backend
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 10. Test endpoint
curl http://localhost:8000/api/v1/recommendations/default?limit=5
```

---

## EXPECTED OUTCOMES AFTER IMPLEMENTATION

| Metric | Before | After |
|---|---|---|
| India/intern keyword matches | ~50 | ~500+ |
| Job sources | 7 | 11 |
| Scoring accuracy | Keyword regex | Gemini semantic |
| Naukri jobs | 0 | 200–500/day |
| Freshersworld jobs | 0 | 100–300/day |
| Remotive jobs | 0 | 200/day |
| Arbeitnow jobs | 0 | 150/day |
| Gemini scoring cost | — | ₹0 (1000 free/day) |

---

## NOTES FOR CLAUDE

- If Naukri returns 0 jobs, their HTML changed. Run `curl "https://www.naukri.com/machine-learning-jobs-in-india" | grep -i "jobTuple\|job-card\|jobCard" | head -5` to find new selectors.
- If Gemini returns 429, you hit rate limit. Increase `asyncio.sleep(2.1)` to `asyncio.sleep(4.0)`.
- Do NOT modify `scrapers/feeds/greenhouse.py`, `lever.py`, `ashby.py` — they work fine.
- Do NOT touch `frontend-integrated/app/layout.tsx` — the `suppressHydrationWarning` fix must stay.
- The `.env` file already has `SERPAPI_KEY`, `RAPIDAPI_KEY`, etc. — append `GEMINI_API_KEY`, don't overwrite.
- All scrapers must handle exceptions silently (print warning, return empty list) so one failure doesn't kill the whole pipeline.
