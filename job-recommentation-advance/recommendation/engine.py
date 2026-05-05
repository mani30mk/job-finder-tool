"""Backward-compatible wrapper for engine_v2.

This allows existing code using `from recommendation.engine import RecommendationEngine`
to work without changes, while getting all v2 improvements.
"""
from recommendation.engine_v2 import (
    RecommendationEngine,
    UserProfile,
    JobMatch,
    ResumeParser,
)

__all__ = ["RecommendationEngine", "UserProfile", "JobMatch", "ResumeParser"]
