# Migration Guide: v1 → v2

## Zero-Code Changes

Your existing code continues to work. The old imports automatically use v2:

```python
# This still works exactly the same
from recommendation.engine import RecommendationEngine

engine = RecommendationEngine()
engine.load_resume("resume.pdf")
matches = engine.recommend_jobs(limit=20)
```

## What is New

### 1. Semantic Matching

```python
from recommendation.engine_v2 import RecommendationEngine

engine = RecommendationEngine()
engine.load_resume("resume.pdf")
# Skills now match semantically, not just by keyword
```

### 2. LLM-Powered Parsing

Set your API key in config or environment:

```bash
export OPENAI_API_KEY="sk-..."
python -m recommendation.cli_v2 --resume resume.pdf --llm
```

### 3. Live Web Search

```bash
python -m recommendation.cli_v2 --resume resume.pdf --web-search
```

### 4. Export Results

```bash
python -m recommendation.cli_v2 --resume resume.pdf --export json
python -m recommendation.cli_v2 --resume resume.pdf --export csv
python -m recommendation.cli_v2 --resume resume.pdf --export markdown
```

### 5. Natural Language Explanations

```python
matches = engine.recommend_jobs(limit=5)
for match in matches:
    print(match.explanation)
    # "The Senior Backend role matches because you have 4 years of Python + Django..."
```

### 6. Dynamic Weights

Weights automatically adjust based on profile:
- Early career (< 2 years): boosts internship matching
- Senior (5+ years): boosts title and experience matching
- Remote preference: boosts location matching

### 7. Skill Inference

```python
# If your resume has "Django", the engine automatically infers:
# - Python
# - Web Development
# - REST API
# - SQL
```

## Config File

Create `config.yaml` to customize everything without code changes:

```yaml
embedding_model: "all-MiniLM-L6-v2"
use_semantic_matching: true
llm_provider: "openai"
llm_api_key: "sk-..."
enable_web_search: true
base_weights:
  skills: 0.35
  title: 0.20
  experience: 0.15
  location: 0.10
  salary: 0.10
  type: 0.10
```

## CLI Comparison

| Task | v1 | v2 |
|------|-----|-----|
| Basic search | `--resume r.pdf` | `--resume r.pdf` |
| With web jobs | Not possible | `--web-search` |
| Export | Not possible | `--export json` |
| Explanations | Not possible | `--explain` |
| Clear cache | Not possible | `--clear-cache` |
| Custom config | Not possible | `--config config.yaml` |

## Breaking Changes

**None.** v2 is fully backward compatible. All v1 APIs work identically.
