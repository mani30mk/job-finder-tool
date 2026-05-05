"""Semantic matching using TF-IDF word-frequency embeddings.

This module uses a lightweight TF-IDF approach for semantic matching
without requiring the heavy sentence-transformers library.
"""
import re
import math
from typing import List, Dict, Optional, Tuple
from collections import Counter


class SemanticMatcher:
    """Match jobs to profiles using TF-IDF based embeddings."""

    def __init__(self, model_name: str = "tfidf", cache_manager=None):
        self.model_name = model_name
        self.cache = cache_manager
        # Build a fixed vocabulary of common tech/job terms for consistent vectors
        self._vocab = None
        self._idf = {}
        print(f"[Semantic] Using TF-IDF fallback matcher")

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        return re.findall(r"\b\w+\b", text.lower())

    def _build_vocab(self, texts: List[str]) -> List[str]:
        """Build vocabulary from given texts."""
        all_words = set()
        for text in texts:
            all_words.update(self._tokenize(text))
        return sorted(all_words)

    def embed(self, text: str) -> List[float]:
        """Get TF-IDF-like embedding vector for text (cached)."""
        if not text:
            return []

        # Check cache
        if self.cache:
            cached = self.cache.get_embedding(text, self.model_name)
            if cached is not None:
                return cached

        embedding = self._tfidf_embed(text)

        # Save to cache
        if self.cache:
            self.cache.save_embedding(text, self.model_name, embedding)

        return embedding

    def _tfidf_embed(self, text: str) -> List[float]:
        """Create a TF-IDF-like word-frequency embedding."""
        words = self._tokenize(text)
        if not words:
            return []

        # Use word frequencies as a simple embedding
        counter = Counter(words)
        vocab = sorted(counter.keys())
        total = len(words)

        # TF: term frequency normalized by total words
        vec = [counter.get(w, 0) / total for w in vocab]

        # Normalize to unit vector
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    def cosine_similarity_sparse(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts using sparse word overlap.

        This avoids the dimension mismatch problem of pre-computed embeddings
        by computing similarity directly from word frequencies.
        """
        words1 = self._tokenize(text1)
        words2 = self._tokenize(text2)

        if not words1 or not words2:
            return 0.0

        counter1 = Counter(words1)
        counter2 = Counter(words2)

        # Common vocabulary
        common_words = set(counter1.keys()) & set(counter2.keys())
        if not common_words:
            return 0.0

        # Dot product over shared words
        dot = sum(counter1[w] * counter2[w] for w in common_words)

        # Magnitudes
        mag1 = math.sqrt(sum(v * v for v in counter1.values()))
        mag2 = math.sqrt(sum(v * v for v in counter2.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot / (mag1 * mag2)

    def match_skills_semantic(self, profile_skills: List[str], job_text: str) -> Tuple[float, List[str]]:
        """Semantically match profile skills to job text using TF-IDF overlap."""
        if not profile_skills:
            return 0.5, []

        job_text_lower = job_text.lower()
        matched = []
        scores = []

        for skill in profile_skills:
            skill_lower = skill.lower()

            # Direct containment check (highest confidence)
            if skill_lower in job_text_lower:
                scores.append(0.9)
                if skill not in matched:
                    matched.append(skill)
                continue

            # TF-IDF cosine similarity for fuzzy matching
            sim = self.cosine_similarity_sparse(skill, job_text)

            # For single-word skills, also check partial word matching
            skill_words = skill_lower.split()
            word_hits = sum(1 for w in skill_words if w in job_text_lower)
            word_ratio = word_hits / len(skill_words) if skill_words else 0

            # Combine TF-IDF sim with word overlap
            combined = max(sim, word_ratio * 0.7)
            scores.append(combined)

            if combined >= 0.4:
                if skill not in matched:
                    matched.append(skill)

        if not scores:
            return 0.0, []

        # Score: average of top matches, with diminishing returns
        scores.sort(reverse=True)
        top_scores = scores[:max(3, len(scores) // 2 + 1)]
        avg_score = sum(top_scores) / len(top_scores)

        # Boost if many skills matched
        coverage = len(matched) / len(profile_skills)
        final_score = min(1.0, avg_score * (1 + coverage * 0.3))

        return final_score, matched

    def match_title_semantic(self, profile_titles: List[str], job_title: str) -> float:
        """Semantically match profile job titles to job title."""
        if not profile_titles:
            return 0.5

        job_title_lower = job_title.lower()
        best_score = 0.0

        for title in profile_titles:
            title_lower = title.lower()

            # Exact containment
            if title_lower in job_title_lower:
                return 1.0

            # Word-level overlap
            title_words = set(title_lower.split())
            job_words = set(job_title_lower.split())
            if title_words and job_words:
                overlap = len(title_words & job_words)
                ratio = overlap / len(title_words)
                best_score = max(best_score, ratio)

            # TF-IDF similarity
            sim = self.cosine_similarity_sparse(title, job_title)
            best_score = max(best_score, sim)

        return best_score

    def compute_job_similarity(self, job1: Dict, job2: Dict) -> float:
        """Compute similarity between two jobs."""
        text1 = "{} {}".format(job1.get("title", ""), job1.get("description", ""))
        text2 = "{} {}".format(job2.get("title", ""), job2.get("description", ""))
        return self.cosine_similarity_sparse(text1, text2)
