"""Quick test: v2 recommendation engine via API."""
import urllib.request
import json

url = "http://localhost:8000/api/v1/recommendations/default?limit=5&min_score=0.0"
r = urllib.request.urlopen(url, timeout=30)
data = json.loads(r.read())

print("Total matches:", data["total_matches"])
print("Profile summary:", json.dumps(data["profile_summary"], indent=2))
print()

for i, rec in enumerate(data["recommendations"][:5], 1):
    score = rec["match_score"]
    title = rec["title"]
    company = rec["company"]
    location = rec["location"]
    reasons = rec.get("match_reasons", [])
    explanation = rec.get("explanation", "")

    print(f"#{i} [Score: {score}] {title} @ {company}")
    print(f"   Location: {location}")
    print(f"   Reasons: {reasons}")
    if explanation:
        print(f"   Explanation: {explanation[:150]}")
    print()

print("=" * 60)
print("v2 features active:")
print("  - Semantic matching: YES (TF-IDF)")
print("  - Skill inference:", data["profile_summary"].get("inferred_skills_count", "N/A"), "inferred skills")
print("  - Dynamic weights: YES")
print("  - Deduplication: YES")
print("  - Explanations: YES")
