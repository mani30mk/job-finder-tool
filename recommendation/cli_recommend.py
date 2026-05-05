"""CLI for job recommendations — find jobs matching your resume.

Usage:
    python -m recommendation.cli --resume path/to/resume.pdf
    python -m recommendation.cli --text "I know Python, React, 2 years experience"
    python -m recommendation.cli --profile profile.json
    python -m recommendation.cli --resume resume.pdf --min-score 0.5 --limit 10
"""
import sys
import argparse
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from recommendation.engine import RecommendationEngine, UserProfile


def print_match(match, rank):
    """Pretty print a job match."""
    job = match.job
    score = match.overall_score

    # Color coding based on score
    if score >= 0.8:
        color = "🟢"
    elif score >= 0.6:
        color = "🟡"
    else:
        color = "🔴"

    print(f"\n{color} Rank #{rank} | Score: {score:.0%}")
    print(f"   📌 {job.get('title', 'Unknown')}")
    print(f"   🏢 {job.get('company', 'Unknown')} | 📍 {job.get('location', 'Remote')}")
    print(f"   💼 {job.get('employment_type', 'Full-time')} | 💰 {job.get('salary', 'Not listed')}")
    print(f"   🔗 {job.get('apply_url', 'No link')[:80]}")

    if match.match_reasons:
        print(f"   ✅ Why: {' | '.join(match.match_reasons)}")

    # Score breakdown
    print(f"   📊 Skills: {match.skill_match_score:.0%} | Title: {match.title_match_score:.0%} | "
          f"Exp: {match.experience_match_score:.0%} | Loc: {match.location_match_score:.0%} | "
          f"Salary: {match.salary_match_score:.0%} | Type: {match.type_match_score:.0%}")


def main():
    parser = argparse.ArgumentParser(description="Job Recommendation Engine")
    parser.add_argument("--resume", type=str, help="Path to resume PDF/DOCX/TXT")
    parser.add_argument("--text", type=str, help="Raw resume text (paste content)")
    parser.add_argument("--profile", type=str, help="Load saved profile JSON")
    parser.add_argument("--limit", type=int, default=20, help="Number of recommendations (default: 20)")
    parser.add_argument("--min-score", type=float, default=0.1, help="Minimum match score 0-1 (default: 0.1)")
    parser.add_argument("--save-profile", type=str, help="Save extracted profile to JSON file")
    parser.add_argument("--details", action="store_true", help="Show full job description")

    args = parser.parse_args()

    # Validate inputs
    if not any([args.resume, args.text, args.profile]):
        print("❌ Error: Provide --resume, --text, or --profile")
        print("\nExamples:")
        print('   python -m recommendation.cli --resume resume.pdf')
        print('   python -m recommendation.cli --text "Python, React, 3 years"')
        print('   python -m recommendation.cli --profile my_profile.json')
        sys.exit(1)

    # Initialize engine
    engine = RecommendationEngine()

    # Load profile
    if args.resume:
        print(f"📄 Parsing resume: {args.resume}")
        engine.load_resume(args.resume)
    elif args.text:
        print(f"📝 Parsing text input...")
        engine.load_profile_text(args.text)
    elif args.profile:
        print(f"📂 Loading profile: {args.profile}")
        engine.load_saved_profile(args.profile)

    # Save profile if requested
    if args.save_profile:
        engine.save_profile(args.save_profile)

    # Get recommendations
    print(f"\n🔍 Finding top {args.limit} matches (min score: {args.min_score:.0%})...")
    matches = engine.recommend_jobs(limit=args.limit, min_score=args.min_score)

    if not matches:
        print("\n😕 No matching jobs found. Try:")
        print("   - Lowering --min-score (e.g., 0.05)")
        print("   - Adding more skills to your resume")
        print("   - Running scrapers to get more jobs: python run_scrapers.py")
        return

    # Print results
    print(f"\n{'='*60}")
    print(f"🎯 TOP {len(matches)} RECOMMENDATIONS")
    print(f"{'='*60}")

    for i, match in enumerate(matches, 1):
        print_match(match, i)

        if args.details and match.job.get('description'):
            desc = match.job['description'][:500]
            print(f"   📝 {desc}...")

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Found {len(matches)} matching jobs")
    print(f"📈 Avg score: {sum(m.overall_score for m in matches) / len(matches):.0%}")
    print(f"\n💡 Tip: Run with --details to see full descriptions")
    print(f"💡 Tip: Save your profile: --save-profile my_profile.json")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
