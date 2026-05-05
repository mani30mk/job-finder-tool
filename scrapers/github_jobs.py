"""GitHub curated job lists scraper."""
import httpx
import re
from typing import List, Dict


class GitHubJobsScraper:
    """Scrape job listings from GitHub curated repos."""

    REPOS = [
        ("remoteintech/remote-jobs", "README.md"),
        ("poteto/hiring-without-whiteboards", "README.md"),
    ]

    async def scrape(self) -> List[Dict]:
        jobs = []

        async with httpx.AsyncClient(timeout=20) as client:
            for repo, file in self.REPOS:
                try:
                    url = f"https://raw.githubusercontent.com/{repo}/main/{file}"
                    print(f"   [GitHub] Fetching {repo}...", end=" ")

                    resp = await client.get(url)
                    if resp.status_code != 200:
                        # Try master branch
                        url = f"https://raw.githubusercontent.com/{repo}/master/{file}"
                        resp = await client.get(url)

                    if resp.status_code != 200:
                        print(f"failed ({resp.status_code})")
                        continue

                    content = resp.text
                    repo_jobs = []

                    # Pattern 1: Markdown links [Company](url)
                    for match in re.finditer(r'-?\s*\[(.*?)\]\((.*?)\)', content):
                        company, link = match.groups()
                        company = company.strip()
                        link = link.strip()

                        if not company or not link.startswith("http"):
                            continue
                        if len(company) > 100:
                            continue

                        repo_jobs.append({
                            "job_id": f"ghub_{hash(link) & 0xFFFFFFFF}",
                            "title": f"Jobs at {company[:50]}",
                            "company": company[:100],
                            "location": "Remote",
                            "employment_type": "Full-time",
                            "description": "",
                            "requirements": "",
                            "apply_url": link,
                            "source_platform": "github",
                            "source_url": link,
                            "posted_date": ""
                        })

                    # Pattern 2: Table rows | Company | Location | URL |
                    for line in content.split("\n"):
                        if "|" in line and ("http" in line or ".com" in line):
                            parts = [p.strip() for p in line.split("|")]
                            if len(parts) >= 3:
                                company = parts[1] if len(parts) > 1 else ""
                                url_match = re.search(r'(https?://[^\s|]+)', line)
                                if url_match and company and len(company) < 100:
                                    link = url_match.group(1)
                                    repo_jobs.append({
                                        "job_id": f"ghub_{hash(link) & 0xFFFFFFFF}",
                                        "title": f"Jobs at {company[:50]}",
                                        "company": company[:100],
                                        "location": parts[2] if len(parts) > 2 else "Remote",
                                        "employment_type": "Full-time",
                                        "apply_url": link,
                                        "source_platform": "github",
                                        "source_url": link,
                                        "posted_date": ""
                                    })

                    print(f"{len(repo_jobs)} jobs")
                    jobs.extend(repo_jobs)

                except Exception as e:
                    print(f"ERROR: {e}")

        return jobs
