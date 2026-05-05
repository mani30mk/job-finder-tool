"""Example usage of JobHunter Advanced v2."""
from recommendation.engine_v2 import RecommendationEngine

# Initialize engine
engine = RecommendationEngine()

# Option 1: Parse resume file
# engine.load_resume("path/to/resume.pdf")

# Option 2: Parse text directly
engine.load_profile_text("""
John Doe
john@example.com

Skills: Python, Django, React, PostgreSQL, Docker, AWS
Experience: 4 years as Full Stack Developer at TechCorp
Education: BS Computer Science

Looking for: Full-time, Remote, $120k+
""")

# Get recommendations
matches = engine.recommend_jobs(limit=10, min_score=0.3)

print(f"Found {len(matches)} matching jobs\n")

for i, match in enumerate(matches, 1):
    job = match.job
    print(f"#{i}: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
    print(f"   Score: {match.overall_score:.0%}")
    print(f"   Why: {' | '.join(match.match_reasons)}")
    print(f"   💬 {match.explanation}")
    print()

# Save profile for reuse
engine.save_profile("my_profile.json")

# Export results
import json
with open("results.json", "w") as f:
    json.dump([m.to_dict() for m in matches], f, indent=2)
print("Results saved to results.json")
