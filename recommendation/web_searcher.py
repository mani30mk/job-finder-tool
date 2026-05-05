"""Live job search from web sources."""
import re
import json
import time
import urllib.parse
from typing import List, Dict, Optional
from datetime import datetime


class WebJobSearcher:
    """Search for live jobs across multiple sources."""

    def __init__(self, max_results: int = 50, delay: float = 1.0):
        self.max_results = max_results
        self.delay = delay
        self.session = None
        self._init_session()

    def _init_session(self):
        """Initialize HTTP session if requests available."""
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
        except ImportError:
            print("[WebSearch] requests not installed. Web search disabled.")

    def search(self, query: str, location: str = "", sources: Optional[List[str]] = None) -> List[Dict]:
        """Search for jobs across configured sources."""
        if not self.session:
            return []

        sources = sources or ["linkedin", "indeed"]
        all_jobs = []

        for source in sources:
            try:
                if source == "linkedin":
                    jobs = self._search_linkedin(query, location)
                elif source == "indeed":
                    jobs = self._search_indeed(query, location)
                else:
                    continue

                all_jobs.extend(jobs)
                time.sleep(self.delay)

                if len(all_jobs) >= self.max_results:
                    break

            except Exception as e:
                print(f"[WebSearch] {source} error: {e}")
                continue

        return all_jobs[:self.max_results]

    def _search_linkedin(self, query: str, location: str) -> List[Dict]:
        """Search LinkedIn jobs (public API scraping)."""
        jobs = []
        try:
            params = {
                "keywords": query,
                "location": location or "United States",
                "f_TPR": "r86400",  # Last 24 hours
                "start": 0
            }
            url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode(params)

            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return []

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            for card in soup.find_all("div", class_="base-card"):
                try:
                    title = card.find("h3", class_="base-search-card__title")
                    company = card.find("h4", class_="base-search-card__subtitle")
                    location_tag = card.find("span", class_="job-search-card__location")
                    link = card.find("a", class_="base-card__full-link")

                    job = {
                        "id": "li_{}".format(hash(title.text if title else '')),
                        "title": title.text.strip() if title else "Unknown",
                        "company": company.text.strip() if company else "Unknown",
                        "location": location_tag.text.strip() if location_tag else "Remote",
                        "description": "",
                        "requirements": "",
                        "employment_type": "full-time",
                        "salary": "Not listed",
                        "salary_min": 0,
                        "salary_max": 0,
                        "apply_url": link["href"] if link and link.has_attr("href") else "",
                        "source": "linkedin",
                        "posted_date": datetime.now().isoformat(),
                        "is_active": 1
                    }
                    jobs.append(job)
                except Exception:
                    continue

        except Exception as e:
            print(f"[WebSearch] LinkedIn error: {e}")

        return jobs

    def _search_indeed(self, query: str, location: str) -> List[Dict]:
        """Search Indeed jobs."""
        jobs = []
        try:
            params = {
                "q": query,
                "l": location or "",
                "fromage": "1"  # Last 24 hours
            }
            url = "https://www.indeed.com/jobs?" + urllib.parse.urlencode(params)

            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return []

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            for card in soup.find_all("div", class_=re.compile("job_seen_beacon|slider_container")):
                try:
                    title = card.find("h2", class_=re.compile("jobTitle"))
                    company = card.find("span", {"data-testid": "company-name"})
                    location_tag = card.find("div", {"data-testid": "text-location"})

                    job = {
                        "id": "indeed_{}".format(hash(title.text if title else '')),
                        "title": title.text.strip() if title else "Unknown",
                        "company": company.text.strip() if company else "Unknown",
                        "location": location_tag.text.strip() if location_tag else "Remote",
                        "description": "",
                        "requirements": "",
                        "employment_type": "full-time",
                        "salary": "Not listed",
                        "salary_min": 0,
                        "salary_max": 0,
                        "apply_url": "",
                        "source": "indeed",
                        "posted_date": datetime.now().isoformat(),
                        "is_active": 1
                    }
                    jobs.append(job)
                except Exception:
                    continue

        except Exception as e:
            print(f"[WebSearch] Indeed error: {e}")

        return jobs

    def search_by_profile(self, profile, max_results: int = 50) -> List[Dict]:
        """Generate search queries from profile and search."""
        queries = []

        # Build queries from skills + job titles
        if profile.job_titles:
            for title in profile.job_titles[:3]:
                queries.append(title)

        if profile.skills:
            skill_query = " ".join(profile.skills[:5])
            queries.append(skill_query)

        if not queries:
            queries.append("software engineer")

        location = ", ".join(profile.locations_preferred[:2]) if profile.locations_preferred else ""

        all_jobs = []
        for q in queries:
            jobs = self.search(q, location, sources=["linkedin", "indeed"])
            all_jobs.extend(jobs)
            if len(all_jobs) >= max_results:
                break

        return all_jobs[:max_results]
