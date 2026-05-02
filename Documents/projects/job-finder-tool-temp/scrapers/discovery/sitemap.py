"""Discover job board URLs from company sitemaps."""
import httpx
from selectolax.parser import HTMLParser
from typing import List, Set
import xml.etree.ElementTree as ET


class SitemapDiscovery:
    """Find career page URLs from sitemap.xml files."""

    COMMON_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-jobs.xml"]
    JOB_KEYWORDS = ["career", "job", "join", "hiring", "opening", "position"]

    async def discover(self, domain: str) -> List[str]:
        """Find job-related URLs from a company's sitemap."""
        found = []
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for path in self.COMMON_PATHS:
                try:
                    urls = await self._parse_sitemap(client, f"https://{domain}{path}")
                    job_urls = [u for u in urls if any(k in u.lower() for k in self.JOB_KEYWORDS)]
                    found.extend(job_urls)
                except Exception:
                    continue
        return list(set(found))

    async def _parse_sitemap(self, client: httpx.AsyncClient, url: str) -> List[str]:
        resp = await client.get(url)
        resp.raise_for_status()

        # Try XML parsing
        try:
            root = ET.fromstring(resp.text)
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = [loc.text for loc in root.findall(".//ns:loc", ns) if loc.text]
            return urls
        except ET.ParseError:
            pass

        # Fallback: regex extract URLs
        import re
        return re.findall(r'<loc>(.*?)</loc>', resp.text)
