"""RemoteOK API scraper."""
import httpx
from typing import List, Dict


class RemoteOKScraper:
    """Scrape RemoteOK API."""

    async def scrape(self) -> List[Dict]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get("https://remoteok.com/api")
                resp.raise_for_status()
                data = resp.json()

                jobs = []
                for job in data:
                    if not isinstance(job, dict):
                        continue

                    jobs.append({
                        "job_id": f"ro_{job.get('id', hash(job.get('position', '')))}",
                        "title": job.get("position", "Unknown")[:200],
                        "company": job.get("company", "Unknown")[:100],
                        "location": job.get("location", "Remote")[:100],
                        "employment_type": "Remote",
                        "description": str(job.get("description", ""))[:3000],
                        "requirements": "",
                        "apply_url": job.get("apply_url", job.get("url", "")),
                        "source_platform": "remoteok",
                        "source_url": job.get("url", ""),
                        "posted_date": job.get("date", "")
                    })

                return jobs
        except Exception as e:
            print(f"   [RemoteOK] Error: {e}")
            return []
