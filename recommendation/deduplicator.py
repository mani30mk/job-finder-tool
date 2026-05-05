"""Job deduplication using semantic similarity and MinHash."""
import re
import hashlib
from typing import List, Dict, Set, Tuple


class JobDeduplicator:
    """Remove duplicate jobs using multiple strategies."""

    def __init__(self, semantic_threshold: float = 0.85):
        self.semantic_threshold = semantic_threshold
        self.seen_hashes: Set[str] = set()
        self.seen_embeddings: List[Tuple[str, List[int]]] = []

    def normalize_text(self, text: str) -> str:
        """Normalize job text for comparison."""
        text = text.lower()
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove punctuation except key separators
        text = re.sub(r"[^\w\s]", "", text)
        # Remove common filler words
        fillers = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words = [w for w in text.split() if w not in fillers and len(w) > 2]
        return " ".join(words)

    def compute_minhash(self, text: str, num_hashes: int = 16) -> List[int]:
        """Compute simple MinHash signature for text."""
        words = self.normalize_text(text).split()
        if not words:
            return [0] * num_hashes

        # Generate shingles (2-grams)
        shingles = set()
        for i in range(len(words) - 1):
            shingle = " ".join(words[i:i+2])
            shingles.add(shingle)

        if not shingles:
            shingles = set(words)

        signatures = []
        for i in range(num_hashes):
            min_hash = float("inf")
            for shingle in shingles:
                hash_val = int(hashlib.md5(f"{shingle}:{i}".encode()).hexdigest(), 16)
                min_hash = min(min_hash, hash_val)
            signatures.append(min_hash)

        return signatures

    def jaccard_similarity(self, sig1: List[int], sig2: List[int]) -> float:
        """Estimate Jaccard similarity from MinHash signatures."""
        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)

    def is_duplicate(self, job: Dict) -> bool:
        """Check if job is a duplicate of previously seen jobs."""
        # Strategy 1: Exact URL match
        url = job.get("apply_url", "") or job.get("url", "")
        if url:
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            if url_hash in self.seen_hashes:
                return True
            self.seen_hashes.add(url_hash)

        # Strategy 2: Exact title+company match
        title = job.get("title", "").strip().lower()
        company = job.get("company", "").strip().lower()
        exact_key = f"{title}||{company}"
        if exact_key in self.seen_hashes:
            return True
        self.seen_hashes.add(exact_key)

        # Strategy 3: MinHash similarity (only when we have enough text)
        desc = job.get("description", "")[:500]
        combined = f"{title} {company} {desc}"

        # Skip MinHash for sparse listings (e.g. Internshala with empty description)
        # — title+company exact match above is sufficient for those
        if len(combined.split()) < 10:
            return False

        sig = self.compute_minhash(combined)

        for seen_id, seen_company, seen_sig in self.seen_embeddings:
            # Only compare MinHash if same company (avoids false positives
            # across different companies with similar generic titles)
            if seen_company == company:
                sim = self.jaccard_similarity(sig, seen_sig)
                if sim >= self.semantic_threshold:
                    return True

        job_id = url or hashlib.sha256(combined.encode()).hexdigest()[:16]
        self.seen_embeddings.append((job_id, company, sig))
        return False

    def deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        """Filter duplicate jobs from a list."""
        # Reset state for each deduplication run
        self.reset()
        unique = []
        for job in jobs:
            if not self.is_duplicate(job):
                unique.append(job)
        return unique

    def reset(self):
        """Clear deduplication state."""
        self.seen_hashes.clear()
        self.seen_embeddings.clear()
