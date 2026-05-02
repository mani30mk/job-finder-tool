"""Deduplication logic."""
import hashlib
from typing import Dict, Set


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
