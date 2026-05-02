"""SerpApi Google Jobs scraper — aggregates LinkedIn, Indeed, Glassdoor, etc.

Sign up at: https://serpapi.com/ to get your API key.
Free tier: 100 searches/month.
Paid plans: $50/mo for 5,000 searches.

This is the BEST LinkedIn replacement because:
- No browser automation needed
- Gets jobs from LinkedIn, Indeed, ZipRecruiter, Glassdoor, company sites
- Structured data with salary, location, posting date
- Works anywhere (local, cloud, serverless)
"""
import httpx
from typing import List, Dict


class SerpApiScraper:
    """Scrape Google Jobs via SerpApi.

    Covers: LinkedIn, Indeed, Glassdoor, ZipRecruiter, Monster, 
            SimplyHired, company career pages, and more.
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(
        self,
        api_key: str = "",
        query: str = "software engineer",
        location: str = "",
        country: str = "us",  # us, uk, ca, in, etc.
        language: str = "en",
        num_results: int = 20,  # Max ~100 per call
        employment_type: str = "",  # FULLTIME, PARTTIME, CONTRACTOR, INTERN
        date_posted: str = "",  # today, 3days, week, month
    ):
        self.api_key = api_key or "YOUR_SERPAPI_KEY"
        self.query = query
        self.location = location
        self.country = country
        self.language = language
        self.num_results = min(num_results, 100)
        self.employment_type = employment_type
        self.date_posted = date_posted

    async def scrape(self) -> List[Dict]:
        if self.api_key == "YOUR_SERPAPI_KEY":
            print("   [SerpApi] WARNING: No API key set. Get free key at serpapi.com")
            print("   [SerpApi] 100 free searches/month. LinkedIn + Indeed + Glassdoor coverage.")
            return []

        params = {
            "engine": "google_jobs",
            "q": self.query,
            "location": self.location,
            "google_domain": f"google.{self.country}",
            "hl": self.language,
            "api_key": self.api_key,
        }

        # Optional filters
        if self.employment_type:
            params["employment_type"] = self.employment_type
        if self.date_posted:
            params["date_posted"] = self.date_posted

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs = []
        job_results = data.get("jobs_results", [])

        for job in job_results:
            # Extract company from extensions or title
            extensions = job.get("extensions", [])
            company = "Unknown"
            location = "Remote"
            posted_date = ""
            employment_type = "Full-time"

            for ext in extensions:
                ext_lower = str(ext).lower()
                if "ago" in ext_lower or "day" in ext_lower or "hour" in ext_lower:
                    posted_date = ext
                elif "remote" in ext_lower or "hybrid" in ext_lower or "on-site" in ext_lower:
                    location = ext
                elif "full-time" in ext_lower or "part-time" in ext_lower or "contract" in ext_lower or "internship" in ext_lower:
                    employment_type = ext
                elif company == "Unknown" and len(str(ext)) < 50:
                    # Heuristic: short strings in extensions are often company names
                    company = ext

            # Try to get company from detected extensions
            detected = job.get("detected_extensions", {})
            if detected.get("posted_at"):
                posted_date = detected["posted_at"]
            if detected.get("schedule_type"):
                employment_type = detected["schedule_type"]

            # Job highlights (requirements, qualifications)
            highlights = job.get("job_highlights", [])
            requirements = ""
            for section in highlights:
                title = section.get("title", "").lower()
                if "qualification" in title or "requirement" in title or "skills" in title:
                    items = section.get("items", [])
                    requirements = " | ".join(items)[:2000]

            # Salary from detected extensions
            salary = detected.get("salary", "")

            jobs.append({
                "job_id": f"serp_{job.get('job_id', hash(job.get('title', '')))}",
                "title": job.get("title", "Unknown")[:200],
                "company": company[:100],
                "location": location[:100],
                "employment_type": employment_type,
                "description": str(job.get("description", ""))[:4000],
                "requirements": requirements,
                "apply_url": job.get("apply_link", job.get("share_link", "")),
                "source_platform": "serpapi_google",
                "source_url": job.get("share_link", ""),
                "posted_date": posted_date,
                "salary": salary,
            })

        # Handle pagination if more results available
        next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
        if next_page_token and len(jobs) < self.num_results:
            # Could recurse here for more pages
            pass

        return jobs
