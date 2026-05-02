"""Adzuna scraper — free tier job API with salary data.

Sign up at: https://developer.adzuna.com/ to get APP_ID and APP_KEY.
Free tier: 100 requests/day (good for testing).
Paid: generous limits for production.
"""
import httpx
from typing import List, Dict


class AdzunaScraper:
    """Scrape jobs from Adzuna API.

    Covers 16+ countries. Includes salary estimates.
    Requires free API key from developer.adzuna.com
    """

    BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

    def __init__(
        self,
        app_id: str = "",
        app_key: str = "",
        country: str = "us",  # us, gb, ca, au, de, fr, in, etc.
        query: str = "software engineer",
        location: str = "",
        max_results: int = 20,
    ):
        self.app_id = app_id or "YOUR_APP_ID"
        self.app_key = app_key or "YOUR_APP_KEY"
        self.country = country
        self.query = query
        self.location = location
        self.max_results = min(max_results, 50)

    async def scrape(self) -> List[Dict]:
        if self.app_id == "YOUR_APP_ID" or self.app_key == "YOUR_APP_KEY":
            print("   [Adzuna] WARNING: No API credentials set. Get free keys at developer.adzuna.com")
            return []

        url = self.BASE_URL.format(country=self.country)
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": self.max_results,
            "what": self.query,
            "where": self.location,
            "content-type": "application/json",
        }
        params = {k: v for k, v in params.items() if v}

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs = []
        for result in data.get("results", []):
            job = result.get("job", {})
            company = result.get("company", {})
            location = result.get("location", {})
            salary = result.get("salary", {})

            jobs.append({
                "job_id": f"adzuna_{result.get('id', '')}",
                "title": job.get("title", "Unknown")[:200],
                "company": company.get("display_name", "Unknown")[:100],
                "location": location.get("display_name", "Remote")[:100],
                "employment_type": job.get("contract_type", "Full-time"),
                "description": str(job.get("description", ""))[:3000],
                "requirements": "",
                "apply_url": job.get("redirect_url", ""),
                "source_platform": "adzuna",
                "source_url": job.get("redirect_url", ""),
                "posted_date": job.get("created_at", ""),
                "salary_min": salary.get("min", ""),
                "salary_max": salary.get("max", ""),
                "salary_currency": salary.get("currency", ""),
            })

        return jobs
