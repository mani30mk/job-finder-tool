# JobHunter Advanced 🎯

An advanced job recommendation engine with semantic matching, LLM-powered parsing, live web search, and intelligent deduplication.

## 🚀 Improvements over v1

| Feature | v1 | v2 (This) |
|---------|-----|-----------|
| Skill Matching | Keyword only | **Semantic + Keyword** |
| Resume Parsing | Regex only | **LLM + Regex fallback** |
| Scoring Weights | Hardcoded | **Dynamic per profile** |
| Skill Inference | None | **Co-occurrence graph** |
| Job Deduplication | None | **MinHash + URL matching** |
| Web Search | None | **LinkedIn, Indeed, etc.** |
| Caching | None | **SQLite cache for all data** |
| Explanations | Template strings | **Natural language generation** |
| Config | Code constants | **YAML/JSON driven** |
| Export | None | **JSON, CSV, Markdown** |

## 📦 Installation

```bash
pip install -r requirements.txt
```

## 🔧 Quick Start

### Basic usage (same as v1)
```bash
python -m recommendation.cli_v2 --resume resume.pdf
python -m recommendation.cli_v2 --text "Python, React, 3 years experience"
```

### Advanced usage
```bash
# Enable web search for live jobs
python -m recommendation.cli_v2 --resume resume.pdf --web-search

# Export to JSON
python -m recommendation.cli_v2 --resume resume.pdf --export json --export-path results.json

# Use custom config
python -m recommendation.cli_v2 --resume resume.pdf --config config.yaml

# Show detailed explanations
python -m recommendation.cli_v2 --resume resume.pdf --explain

# Clear cache and re-parse
python -m recommendation.cli_v2 --resume resume.pdf --clear-cache
```

## ⚙️ Configuration

Create `config.yaml`:

```yaml
db_path: "jobs.db"
cache_path: ".jobhunter_cache.db"

# Semantic matching
embedding_model: "all-MiniLM-L6-v2"
use_semantic_matching: true

# LLM parsing (requires API key)
llm_provider: "openai"
llm_model: "gpt-3.5-turbo"
llm_api_key: "sk-..."
use_llm_parsing: true

# Web search
enable_web_search: true
max_web_jobs: 50

# Scoring
base_weights:
  skills: 0.35
  title: 0.20
  experience: 0.15
  location: 0.10
  salary: 0.10
  type: 0.10
```

## 🏗️ Architecture

```
jobhunter_advanced/
├── recommendation/
│   ├── __init__.py
│   ├── engine_v2.py          # Core engine (backward compatible)
│   ├── cli_v2.py             # Advanced CLI
│   ├── config.py             # Config management
│   ├── cache_manager.py      # SQLite caching
│   ├── semantic_matcher.py   # Embedding-based matching
│   ├── deduplicator.py       # MinHash deduplication
│   ├── enricher.py           # Skill inference
│   ├── llm_parser.py         # LLM resume parsing
│   └── web_searcher.py       # Live job search
├── requirements.txt
└── README.md
```

## 🧪 Programmatic Usage

```python
from recommendation.engine_v2 import RecommendationEngine

engine = RecommendationEngine(config_path="config.yaml")
engine.load_resume("resume.pdf")

# Get recommendations
matches = engine.recommend_jobs(limit=10, min_score=0.5)

for match in matches:
    print(f"{match.job['title']}: {match.overall_score:.0%}")
    print(match.explanation)  # Natural language explanation
```

## 📄 License

MIT
