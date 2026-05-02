"""TheirStack scraper — job API with LinkedIn + company site coverage.

Sign up at: https://theirstack.com/en/jobs-api to get your API key.
Free tier: 200 credits/month (1 credit = 1 job result).
Paid plans: $49/mo for 10,000 credits.

Covers: LinkedIn, Indeed, Glassdoor, company career pages, and more.
"""
import httpx
from typing import List, Dict


class TheirStackScraper:
    """Scrape jobs from TheirStack API.

    Best for: tech jobs, startup jobs, remote jobs.
    Includes: salary, seniority, tech stack, remote policy.
    """

    BASE_URL = "https://api.theirstack.com/jobs/search"

    def __init__(
        self,
        api_key: str = "",
        query: str = "software engineer",
        location: str = "",
        remote_only: bool = False,
        max_results: int = 50,
        posted_within_days: int = 30,
    ):
        self.api_key = api_key or "YOUR_THEIRSTACK_KEY"
        self.query = query
        self.location = location
        self.remote_only = remote_only
        self.max_results = min(max_results, 100)
        self.posted_within_days = posted_within_days

    async def scrape(self) -> List[Dict]:
        if self.api_key == "YOUR_THEIRSTACK_KEY":
            print("   [TheirStack] WARNING: No API key set. Get free key at theirstack.com")
            print("   [TheirStack] 200 free credits/month. LinkedIn + Indeed + company sites.")
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": self.query,
            "limit": self.max_results,
            "posted_within_days": self.posted_within_days,
        }

        if self.location:
            payload["location"] = self.location
        if self.remote_only:
            payload["remote_only"] = True

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.BASE_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        jobs = []
        for job in data.get("data", []):
            company = job.get("company", {})
            location_data = job.get("location", {})
            salary = job.get("salary", {})
            tech_stack = job.get("tech_stack", [])

            # Build apply URL from theirstack redirect or direct link
            apply_url = job.get("url", "")
            if not apply_url and job.get("id"):
                apply_url = f"https://theirstack.com/jobs/{job['id']}"

            jobs.append({
                "job_id": f"ts_{job.get('id', '')}",
                "title": job.get("title", "Unknown")[:200],
                "company": company.get("name", "Unknown")[:100],
                "location": location_data.get("display_name", "Remote")[:100],
                "employment_type": job.get("employment_type", "Full-time"),
                "description": str(job.get("description", ""))[:4000],
                "requirements": " | ".join(tech_stack)[:2000] if tech_stack else "",
                "apply_url": apply_url,
                "source_platform": "theirstack",
                "source_url": apply_url,
                "posted_date": job.get("date_posted", ""),
                "salary_min": salary.get("min", ""),
                "salary_max": salary.get("max", ""),
                "salary_currency": salary.get("currency", ""),
                "remote_policy": job.get("remote_policy", ""),
                "seniority": job.get("seniority", ""),
            })

        return jobs
