"""Normalize raw job data into standard schema."""
from typing import Dict, Any


def normalize_job(raw: Dict[str, Any]) -> Dict[str, str]:
    """Ensure all required fields exist with sensible defaults."""
    return {
        "job_id": str(raw.get("job_id", "")),
        "title": str(raw.get("title", "Unknown"))[:300],
        "company": str(raw.get("company", "Unknown"))[:200],
        "location": str(raw.get("location", "Remote"))[:200],
        "employment_type": str(raw.get("employment_type", "Full-time"))[:50],
        "description": str(raw.get("description", ""))[:10000],
        "requirements": str(raw.get("requirements", ""))[:5000],
        "apply_url": str(raw.get("apply_url", ""))[:1000],
        "source_platform": str(raw.get("source_platform", "unknown"))[:50],
        "source_url": str(raw.get("source_url", ""))[:1000],
        "posted_date": str(raw.get("posted_date", ""))[:50],
    }
