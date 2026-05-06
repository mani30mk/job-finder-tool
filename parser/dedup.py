"""Deduplication logic."""
import hashlib
from typing import Dict, Set

# Optional: fuzzy deduplication with rapidfuzz
try:
    from rapidfuzz import fuzz as _fuzz
    _RAPIDFUZZ_AVAILABLE = True
except ImportError:
    _RAPIDFUZZ_AVAILABLE = False


class Deduplicator:
    @staticmethod
    def generate_id(job: Dict) -> str:
        """Create unique hash from normalized title + company + location."""
        key = "|".join([
            job.get("title", "").lower().strip(),
            job.get("company", "").lower().strip(),
            job.get("location", "").lower().strip()
        ])
        return hashlib.md5(key.encode()).hexdigest()

    @staticmethod
    def is_duplicate(job: Dict, existing_ids: Set[str]) -> bool:
        return Deduplicator.generate_id(job) in existing_ids


def is_fuzzy_duplicate(new_title: str, new_company: str,
                        existing_title: str, existing_company: str) -> bool:
    """
    Returns True if two jobs are likely the same posting.
    Catches variants like 'SDE Intern' vs 'Software Development Engineer Intern'.
    """
    if not _RAPIDFUZZ_AVAILABLE:
        return False
    title_sim   = _fuzz.token_sort_ratio(new_title.lower(), existing_title.lower())
    company_sim = _fuzz.ratio(new_company.lower(), existing_company.lower())
    return title_sim >= 85 and company_sim >= 88

