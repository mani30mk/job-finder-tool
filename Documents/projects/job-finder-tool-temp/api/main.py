"""FastAPI backend — Job Recommendation API for mobile + web.

Endpoints:
    POST /api/v1/profile/upload      — Upload resume (PDF/DOCX/TXT)
    POST /api/v1/profile/text        — Submit profile as raw text
    POST /api/v1/profile/manual      — Submit structured profile JSON
    GET  /api/v1/profile/me          — Get current user profile
    POST /api/v1/recommendations     — Get job recommendations
    GET  /api/v1/jobs/{job_id}       — Get single job details
    GET  /api/v1/jobs/search         — Search jobs with filters
    POST /api/v1/jobs/{job_id}/save  — Save/bookmark a job
    GET  /api/v1/saved-jobs          — Get saved jobs
    GET  /api/v1/stats               — Get recommendation stats

Run:
    uvicorn api.main:app --reload --port 8000
"""
import os
import json
import uuid
import shutil
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from recommendation.engine import RecommendationEngine, UserProfile, ResumeParser

# ─── Configuration ───
UPLOAD_DIR = Path("uploads/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path("jobs.db")

# In-memory session store (replace with Redis in production)
user_sessions: Dict[str, Dict] = {}

# ─── Pydantic Models ───

class ProfileTextRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Resume text content")
    name: Optional[str] = None
    email: Optional[str] = None

class ProfileManualRequest(BaseModel):
    name: str = ""
    email: str = ""
    skills: List[str] = []
    experience_years: float = 0.0
    education: List[str] = []
    job_titles: List[str] = []
    locations_preferred: List[str] = []
    remote_preference: str = "any"
    salary_min: int = 0
    salary_max: int = 0
    employment_types: List[str] = ["full-time", "internship"]

class RecommendationRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.1, ge=0.0, le=1.0)
    filters: Optional[Dict] = None

class JobResponse(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    employment_type: str
    description: str
    apply_url: str
    source_platform: str
    posted_date: str
    salary: Optional[str] = None
    match_score: Optional[float] = None
    match_reasons: Optional[List[str]] = None

class RecommendationResponse(BaseModel):
    user_id: str
    total_matches: int
    recommendations: List[JobResponse]
    profile_summary: Dict

class StatsResponse(BaseModel):
    total_jobs: int
    active_jobs: int
    total_sources: int
    top_sources: List[Dict]
    last_scraped: Optional[str] = None

# ─── FastAPI App ───

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events."""
    print("🚀 API starting up...")
    yield
    print("🛑 API shutting down...")

app = FastAPI(
    title="Job Hunter API",
    description="Job recommendation API for mobile and web apps",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Helper Functions ───

def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def get_or_create_user(user_id: Optional[str] = None) -> str:
    """Get existing user or create new session."""
    if user_id and user_id in user_sessions:
        return user_id
    new_id = str(uuid.uuid4())[:8]
    user_sessions[new_id] = {"created": datetime.now().isoformat()}
    return new_id

def profile_to_dict(profile: UserProfile) -> Dict:
    return {
        "name": profile.name,
        "email": profile.email,
        "skills": profile.skills,
        "experience_years": profile.experience_years,
        "education": profile.education,
        "job_titles": profile.job_titles,
        "locations_preferred": profile.locations_preferred,
        "remote_preference": profile.remote_preference,
        "salary_min": profile.salary_min,
        "salary_max": profile.salary_max,
        "employment_types": profile.employment_types,
    }

# ─── API Endpoints ───

@app.get("/")
async def root():
    return {
        "service": "Job Hunter API",
        "version": "2.0.0",
        "endpoints": {
            "profile_upload": "POST /api/v1/profile/upload",
            "profile_text": "POST /api/v1/profile/text",
            "recommendations": "POST /api/v1/recommendations",
            "jobs_search": "GET /api/v1/jobs/search",
            "stats": "GET /api/v1/stats",
        }
    }

@app.post("/api/v1/profile/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
):
    """Upload resume file (PDF/DOCX/TXT) and extract profile."""
    uid = get_or_create_user(user_id)

    # Validate file type
    allowed = {".pdf", ".docx", ".txt", ".md"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Invalid file type. Allowed: {allowed}")

    # Save file
    filename = f"{uid}_{file.filename}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse resume
    try:
        engine = RecommendationEngine()
        profile = engine.load_resume(str(filepath))

        # Store in session
        user_sessions[uid]["profile"] = profile
        user_sessions[uid]["resume_path"] = str(filepath)

        return {
            "user_id": uid,
            "message": "Resume parsed successfully",
            "profile": profile_to_dict(profile),
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to parse resume: {str(e)}")

@app.post("/api/v1/profile/text")
async def profile_from_text(request: ProfileTextRequest, user_id: Optional[str] = Query(None)):
    """Submit profile from raw text (no file upload)."""
    uid = get_or_create_user(user_id)

    engine = RecommendationEngine()
    profile = engine.load_profile_text(request.text)

    if request.name:
        profile.name = request.name
    if request.email:
        profile.email = request.email

    user_sessions[uid]["profile"] = profile

    return {
        "user_id": uid,
        "message": "Profile created from text",
        "profile": profile_to_dict(profile),
    }

@app.post("/api/v1/profile/manual")
async def profile_manual(request: ProfileManualRequest, user_id: Optional[str] = Query(None)):
    """Submit structured profile manually (form/mobile app)."""
    uid = get_or_create_user(user_id)

    profile = UserProfile(
        name=request.name,
        email=request.email,
        skills=[s.lower().strip() for s in request.skills],
        experience_years=request.experience_years,
        education=request.education,
        job_titles=[t.lower().strip() for t in request.job_titles],
        locations_preferred=[l.lower().strip() for l in request.locations_preferred],
        remote_preference=request.remote_preference,
        salary_min=request.salary_min,
        salary_max=request.salary_max,
        employment_types=[t.lower().strip() for t in request.employment_types],
    )

    user_sessions[uid]["profile"] = profile

    return {
        "user_id": uid,
        "message": "Manual profile saved",
        "profile": profile_to_dict(profile),
    }

@app.get("/api/v1/profile/me")
async def get_profile(user_id: str):
    """Get current user profile."""
    if user_id not in user_sessions or "profile" not in user_sessions[user_id]:
        raise HTTPException(404, "Profile not found. Upload resume first.")

    profile = user_sessions[user_id]["profile"]
    return {
        "user_id": user_id,
        "profile": profile_to_dict(profile),
    }

@app.post("/api/v1/recommendations")
async def get_recommendations(
    request: RecommendationRequest,
    user_id: str = Query(..., description="User session ID"),
):
    """Get personalized job recommendations."""
    if user_id not in user_sessions or "profile" not in user_sessions[user_id]:
        raise HTTPException(404, "Profile not found. Upload resume first.")

    profile = user_sessions[user_id]["profile"]

    # Generate recommendations
    engine = RecommendationEngine()
    engine.set_profile(profile)
    matches = engine.recommend_jobs(limit=request.limit, min_score=request.min_score)

    # Convert to response format
    recommendations = []
    for match in matches:
        job = match.job
        recommendations.append(JobResponse(
            job_id=job.get("job_id", ""),
            title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            employment_type=job.get("employment_type", ""),
            description=job.get("description", "")[:500],
            apply_url=job.get("apply_url", ""),
            source_platform=job.get("source_platform", ""),
            posted_date=job.get("posted_date", ""),
            salary=job.get("salary", None),
            match_score=round(match.overall_score, 2),
            match_reasons=match.match_reasons,
        ))

    return RecommendationResponse(
        user_id=user_id,
        total_matches=len(recommendations),
        recommendations=recommendations,
        profile_summary={
            "skills_count": len(profile.skills),
            "top_skills": profile.skills[:5],
            "experience_years": profile.experience_years,
            "preferred_types": profile.employment_types,
        },
    )

@app.get("/api/v1/jobs/search")
async def search_jobs(
    q: Optional[str] = Query(None, description="Search query"),
    location: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    remote: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Search jobs with filters (no personalization)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM jobs WHERE is_active = 1"
    params = []

    if q:
        query += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if employment_type:
        query += " AND employment_type LIKE ?"
        params.append(f"%{employment_type}%")
    if source:
        query += " AND source_platform = ?"
        params.append(source)

    query += " ORDER BY posted_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    jobs = []
    for row in rows:
        jobs.append({
            "job_id": row["job_id"],
            "title": row["title"],
            "company": row["company"],
            "location": row["location"],
            "employment_type": row["employment_type"],
            "description": row["description"][:300] if row["description"] else "",
            "apply_url": row["apply_url"],
            "source_platform": row["source_platform"],
            "posted_date": row["posted_date"],
        })

    return {"total": len(jobs), "jobs": jobs, "offset": offset, "limit": limit}

@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str):
    """Get single job details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, "Job not found")

    return {
        "job_id": row["job_id"],
        "title": row["title"],
        "company": row["company"],
        "location": row["location"],
        "employment_type": row["employment_type"],
        "description": row["description"],
        "requirements": row["requirements"],
        "apply_url": row["apply_url"],
        "source_platform": row["source_platform"],
        "source_url": row["source_url"],
        "posted_date": row["posted_date"],
    }

@app.post("/api/v1/jobs/{job_id}/save")
async def save_job(job_id: str, user_id: str = Query(...)):
    """Save/bookmark a job for later."""
    if user_id not in user_sessions:
        raise HTTPException(404, "User not found")

    if "saved_jobs" not in user_sessions[user_id]:
        user_sessions[user_id]["saved_jobs"] = []

    if job_id not in user_sessions[user_id]["saved_jobs"]:
        user_sessions[user_id]["saved_jobs"].append(job_id)

    return {"message": "Job saved", "saved_count": len(user_sessions[user_id]["saved_jobs"])}

@app.get("/api/v1/saved-jobs")
async def get_saved_jobs(user_id: str):
    """Get all saved jobs for a user."""
    if user_id not in user_sessions or "saved_jobs" not in user_sessions[user_id]:
        return {"jobs": []}

    job_ids = user_sessions[user_id]["saved_jobs"]

    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(job_ids))
    cursor.execute(f"SELECT * FROM jobs WHERE job_id IN ({placeholders})", job_ids)
    rows = cursor.fetchall()
    conn.close()

    jobs = []
    for row in rows:
        jobs.append({
            "job_id": row["job_id"],
            "title": row["title"],
            "company": row["company"],
            "location": row["location"],
            "employment_type": row["employment_type"],
            "apply_url": row["apply_url"],
        })

    return {"jobs": jobs}

@app.get("/api/v1/stats")
async def get_stats():
    """Get database and scraper statistics."""
    from database.db import get_stats as db_stats
    stats = db_stats()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Top sources
    cursor.execute("""
        SELECT source_platform, COUNT(*) as count 
        FROM jobs 
        WHERE is_active = 1 
        GROUP BY source_platform 
        ORDER BY count DESC
    """)
    sources = [{"name": row["source_platform"], "count": row["count"]} for row in cursor.fetchall()]
    conn.close()

    return StatsResponse(
        total_jobs=stats.get("total", 0),
        active_jobs=stats.get("active", 0),
        total_sources=len(sources),
        top_sources=sources,
        last_scraped=stats.get("last_scraped", None),
    )