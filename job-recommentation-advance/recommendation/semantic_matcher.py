"""Semantic matching using embeddings."""
import re
import numpy as np
from typing import List, Dict, Optional, Tuple


class SemanticMatcher:
    """Match jobs to profiles using semantic embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_manager=None):
        self.model_name = model_name
        self.cache = cache_manager
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load sentence transformer model if available."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            print(f"[Semantic] Loaded model: {self.model_name}")
        except ImportError:
            print("[Semantic] sentence-transformers not installed. Using TF-IDF fallback.")
            self.model = None

    def embed(self, text: str) -> List[float]:
        """Get embedding vector for text (cached)."""
        if not text:
            return []

        # Check cache
        if self.cache:
            cached = self.cache.get_embedding(text, self.model_name)
            if cached is not None:
                return cached

        if self.model:
            embedding = self.model.encode(text, convert_to_numpy=True).tolist()
        else:
            # Fallback: simple word frequency vector
            embedding = self._fallback_embed(text)

        # Save to cache
        if self.cache:
            self.cache.save_embedding(text, self.model_name, embedding)

        return embedding

    def _fallback_embed(self, text: str) -> List[float]:
        """Simple word-frequency embedding fallback."""
        words = re.findall(r"\b\w+\b", text.lower())
        vocab = sorted(set(words))
        vec = [words.count(w) for w in vocab]
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        # Handle different dimensions (fallback vs transformer)
        if len(v1) != len(v2):
            return 0.0

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(v1, v2) / (norm1 * norm2))

    def match_skills_semantic(self, profile_skills: List[str], job_text: str) -> Tuple[float, List[str]]:
        """Semantically match profile skills to job text."""
        if not profile_skills:
            return 0.5, []

        job_embedding = self.embed(job_text)
        if not job_embedding:
            return 0.0, []

        matched = []
        scores = []

        for skill in profile_skills:
            skill_embedding = self.embed(skill)
            if not skill_embedding:
                continue

            sim = self.cosine_similarity(skill_embedding, job_embedding)
            scores.append(sim)

            # Also check direct containment as boost
            if skill.lower() in job_text.lower():
                sim = max(sim, 0.9)
                if skill not in matched:
                    matched.append(skill)
            elif sim >= 0.5:  # Semantic match threshold
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

        job_emb = self.embed(job_title)
        if not job_emb:
            return 0.0

        best_score = 0.0
        for title in profile_titles:
            title_emb = self.embed(title)
            if not title_emb:
                continue
            sim = self.cosine_similarity(title_emb, job_emb)
            best_score = max(best_score, sim)

        return best_score

    def compute_job_similarity(self, job1: Dict, job2: Dict) -> float:
        """Compute similarity between two jobs."""
        text1 = f"{job1.get("title", "")} {job1.get("description", "")}"
        text2 = f"{job2.get("title", "")} {job2.get("description", "")}"

        emb1 = self.embed(text1)
        emb2 = self.embed(text2)

        return self.cosine_similarity(emb1, emb2)
