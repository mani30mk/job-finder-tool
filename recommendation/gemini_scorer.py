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
