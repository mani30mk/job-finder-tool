"""Configuration management for JobHunter Advanced."""
import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict

# Optional YAML support
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class ScoringWeights:
    """Dynamic scoring weights."""
    skills: float = 0.35
    title: float = 0.20
    experience: float = 0.15
    location: float = 0.10
    salary: float = 0.10
    type: float = 0.10


@dataclass
class Config:
    """Application configuration."""
    # Database
    db_path: str = ""
    cache_path: str = ".jobhunter_cache.db"

    # Semantic matching
    embedding_model: str = "tfidf"  # Using TF-IDF fallback (no sentence-transformers)
    similarity_threshold: float = 0.65
    use_semantic_matching: bool = True

    # LLM Parsing (requires API key)
    llm_provider: str = "openai"  # openai, anthropic, none
    llm_model: str = "gpt-3.5-turbo"
    llm_api_key: str = ""
    use_llm_parsing: bool = False

    # Web search
    enable_web_search: bool = False
    search_sources: List[str] = field(default_factory=lambda: [
        "linkedin", "indeed"
    ])
    max_web_jobs: int = 50

    # Deduplication
    dedup_threshold: float = 0.85

    # Scoring
    base_weights: ScoringWeights = field(default_factory=ScoringWeights)

    # Output
    default_limit: int = 20
    default_min_score: float = 0.1

    def __post_init__(self):
        # Resolve db_path relative to project root if not set
        if not self.db_path:
            self.db_path = str(Path(__file__).resolve().parent.parent / "jobs.db")
        # Resolve cache_path relative to project root
        if self.cache_path and not Path(self.cache_path).is_absolute():
            self.cache_path = str(Path(__file__).resolve().parent.parent / self.cache_path)
        # Read LLM API key from environment if not provided
        if not self.llm_api_key:
            self.llm_api_key = os.environ.get("OPENAI_API_KEY", "")

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load config from YAML or JSON."""
        path = Path(path)
        if not path.exists():
            return cls()

        text = path.read_text()
        if path.suffix in (".yaml", ".yml"):
            if HAS_YAML:
                data = yaml.safe_load(text)
            else:
                data = json.loads(text)
        else:
            data = json.loads(text)

        # Handle nested weights
        weights_data = data.pop("base_weights", {})
        weights = ScoringWeights(**weights_data)

        return cls(base_weights=weights, **data)

    def to_file(self, path: str):
        """Save config to file."""
        path = Path(path)
        data = asdict(self)
        if path.suffix in (".yaml", ".yml"):
            if HAS_YAML:
                path.write_text(yaml.dump(data, default_flow_style=False))
            else:
                path.write_text(json.dumps(data, indent=2))
        else:
            path.write_text(json.dumps(data, indent=2))

    def get_dynamic_weights(self, profile) -> Dict[str, float]:
        """Adjust weights based on profile characteristics."""
        w = asdict(self.base_weights)

        # Early career: boost type match (internships), reduce experience weight
        if profile.experience_years < 2:
            w["experience"] *= 0.5
            w["type"] *= 1.5
            w["skills"] *= 1.2

        # Senior: boost experience and title match
        elif profile.experience_years >= 5:
            w["experience"] *= 1.3
            w["title"] *= 1.2
            w["skills"] *= 0.9

        # Remote preference strong: boost location weight
        if profile.remote_preference == "remote":
            w["location"] *= 1.5

        # Normalize to sum to 1.0
        total = sum(w.values())
        return {k: v / total for k, v in w.items()}
