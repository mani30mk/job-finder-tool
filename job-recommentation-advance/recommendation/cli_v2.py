"""Advanced CLI for job recommendations — find jobs matching your resume.

Usage:
    python -m recommendation.cli_v2 --resume path/to/resume.pdf
    python -m recommendation.cli_v2 --text "I know Python, React, 2 years experience"
    python -m recommendation.cli_v2 --profile profile.json
    python -m recommendation.cli_v2 --resume resume.pdf --min-score 0.5 --limit 10 --export json
    python -m recommendation.cli_v2 --resume resume.pdf --semantic --llm --web-search
"""
import sys
import argparse
import json
import csv
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from recommendation.engine_v2 import RecommendationEngine, UserProfile, JobMatch


def print_match(match: JobMatch, rank: int):
    """Pretty print a job match with rich formatting."""
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
        reasons = " | ".join(match.match_reasons)
        print(f"   ✅ Why: {reasons}")
    
    # Natural language explanation
    if match.explanation:
        print(f"   💬 {match.explanation}")

    # Score breakdown
    print(f"   📊 Skills: {match.skill_match_score:.0%} | Title: {match.title_match_score:.0%} | "
          f"Exp: {match.experience_match_score:.0%} | Loc: {match.location_match_score:.0%} | "
          f"Salary: {match.salary_match_score:.0%} | Type: {match.type_match_score:.0%}")


def export_json(matches: list, filepath: str):
    """Export matches to JSON."""
    data = [m.to_dict() for m in matches]
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n📁 Exported {len(matches)} matches to {filepath}")


def export_csv(matches: list, filepath: str):
    """Export matches to CSV."""
    if not matches:
        return
    
    keys = ["title", "company", "location", "employment_type", "salary", "apply_url", "source"]
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "overall_score", "skill_match", "title_match", 
                        "experience_match", "location_match", "salary_match", "type_match",
                        "reasons", "explanation"] + keys)
        
        for i, match in enumerate(matches, 1):
            job = match.job
            row = [
                i, match.overall_score, match.skill_match_score, match.title_match_score,
                match.experience_match_score, match.location_match_score, 
                match.salary_match_score, match.type_match_score,
                " | ".join(match.match_reasons), match.explanation
            ] + [job.get(k, "") for k in keys]
            writer.writerow(row)
    
    print(f"\n📁 Exported {len(matches)} matches to {filepath}")


def export_markdown(matches: list, filepath: str):
    """Export matches to Markdown."""
    from datetime import datetime
    lines = ["# Job Recommendations\n", f"Generated: {datetime.now().isoformat()}\n\n"]
    
    for i, match in enumerate(matches, 1):
        job = match.job
        lines.append(f"## #{i} — {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}\n\n")
        lines.append(f"- **Match Score:** {match.overall_score:.0%}\n")
        lines.append(f"- **Location:** {job.get('location', 'Remote')}\n")
        lines.append(f"- **Type:** {job.get('employment_type', 'Full-time')}\n")
        lines.append(f"- **Salary:** {job.get('salary', 'Not listed')}\n")
        lines.append(f"- **Apply:** {job.get('apply_url', 'No link')}\n\n")
        lines.append(f"**Why:** {" | ".join(match.match_reasons)}\n\n")
        lines.append(f"**Explanation:** {match.explanation}\n\n")
        lines.append("---\n\n")
    
    with open(filepath, "w") as f:
        f.writelines(lines)
    
    print(f"\n📁 Exported {len(matches)} matches to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Job Recommendation Engine v2 (Advanced)")
    parser.add_argument("--resume", type=str, help="Path to resume PDF/DOCX/TXT")
    parser.add_argument("--text", type=str, help="Raw resume text (paste content)")
    parser.add_argument("--profile", type=str, help="Load saved profile JSON")
    parser.add_argument("--limit", type=int, default=20, help="Number of recommendations (default: 20)")
    parser.add_argument("--min-score", type=float, default=0.1, help="Minimum match score 0-1 (default: 0.1)")
    parser.add_argument("--save-profile", type=str, help="Save extracted profile to JSON file")
    parser.add_argument("--details", action="store_true", help="Show full job description")
    
    # Advanced options
    parser.add_argument("--config", type=str, help="Path to config YAML/JSON")
    parser.add_argument("--semantic", action="store_true", help="Enable semantic matching (default: on)")
    parser.add_argument("--no-semantic", action="store_true", help="Disable semantic matching")
    parser.add_argument("--llm", action="store_true", help="Enable LLM parsing if API key configured")
    parser.add_argument("--web-search", action="store_true", help="Enable live web job search")
    parser.add_argument("--export", type=str, choices=["json", "csv", "markdown"], help="Export results to file")
    parser.add_argument("--export-path", type=str, help="Export file path (auto-generated if not set)")
    parser.add_argument("--clear-cache", action="store_true", help="Clear all caches before running")
    parser.add_argument("--explain", action="store_true", help="Show detailed natural language explanations")

    args = parser.parse_args()

    # Validate inputs
    if not any([args.resume, args.text, args.profile]):
        print("❌ Error: Provide --resume, --text, or --profile")
        print("\nExamples:")
        print('   python -m recommendation.cli_v2 --resume resume.pdf')
        print('   python -m recommendation.cli_v2 --text "Python, React, 3 years"')
        print('   python -m recommendation.cli_v2 --profile my_profile.json')
        print('   python -m recommendation.cli_v2 --resume resume.pdf --web-search --export json')
        sys.exit(1)

    # Initialize engine
    engine = RecommendationEngine(config_path=args.config)
    
    # Override config from CLI args
    if args.no_semantic:
        engine.config.use_semantic_matching = False
    if args.llm:
        engine.config.use_llm_parsing = True
    if args.web_search:
        engine.config.enable_web_search = True
    
    # Clear cache if requested
    if args.clear_cache:
        engine.clear_cache()

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
        print("   - Enabling --web-search for live jobs")
        print("   - Running scrapers to get more jobs: python run_scrapers.py")
        return

    # Print results
    print(f"\n{"="*70}")
    print(f"🎯 TOP {len(matches)} RECOMMENDATIONS")
    print(f"{"="*70}")

    for i, match in enumerate(matches, 1):
        print_match(match, i)

        if args.details and match.job.get('description'):
            desc = match.job['description'][:500]
            print(f"   📝 {desc}...")
        
        if args.explain and match.explanation:
            print(f"   💬 {match.explanation}")

    # Summary
    avg_score = sum(m.overall_score for m in matches) / len(matches)
    print(f"\n{"="*70}")
    print(f"✅ Found {len(matches)} matching jobs")
    print(f"📈 Avg score: {avg_score:.0%}")
    print(f"🔧 Semantic matching: {'ON' if engine.config.use_semantic_matching else 'OFF'}")
    print(f"🤖 LLM parsing: {'ON' if engine.llm_parser else 'OFF'}")
    print(f"🌐 Web search: {'ON' if engine.web_searcher else 'OFF'}")
    print(f"\n💡 Tip: Run with --details to see full descriptions")
    print(f"💡 Tip: Export results: --export json --export-path results.json")
    print(f"💡 Tip: Save your profile: --save-profile my_profile.json")
    print(f"{"="*70}")

    # Export if requested
    if args.export:
        export_path = args.export_path or f"recommendations.{args.export}"
        if args.export == "json":
            export_json(matches, export_path)
        elif args.export == "csv":
            export_csv(matches, export_path)
        elif args.export == "markdown":
            export_markdown(matches, export_path)


if __name__ == "__main__":
    main()
