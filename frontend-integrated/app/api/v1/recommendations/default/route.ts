import { NextResponse } from "next/server";
import { turso } from "@/lib/turso";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get("limit") || "50");
  const minScore = parseFloat(searchParams.get("min_score") || "0.0");

  try {
    // We prioritize jobs with a gemini_score > minScore, falling back to recent active jobs
    // In a real semantic search without Python, we rely on the pre-computed gemini_score
    const result = await turso.execute({
      sql: `
        SELECT * FROM jobs 
        WHERE is_active = 1 AND (gemini_score >= ? OR gemini_score IS NULL)
        ORDER BY gemini_score DESC, posted_date DESC 
        LIMIT ?
      `,
      args: [minScore, limit]
    });

    const recommendations = result.rows.map(row => {
      let match_reasons: string[] = [];
      try {
        if (typeof row.gemini_reasons === "string" && row.gemini_reasons) {
          match_reasons = JSON.parse(row.gemini_reasons);
        }
      } catch (e) {
        // ignore JSON parse error
      }

      return {
        job_id: String(row.job_id || ""),
        title: String(row.title || ""),
        company: String(row.company || ""),
        location: String(row.location || ""),
        employment_type: String(row.employment_type || ""),
        description: String(row.description || "").substring(0, 500),
        apply_url: String(row.apply_url || ""),
        source_platform: String(row.source_platform || ""),
        posted_date: String(row.posted_date || ""),
        salary: row.salary ? String(row.salary) : null,
        match_score: row.gemini_score ? Number(row.gemini_score) : 0,
        match_reasons: match_reasons.length > 0 ? match_reasons : ["Matches default profile"],
        gemini_summary: row.gemini_summary ? String(row.gemini_summary) : ""
      };
    });

    return NextResponse.json({
      user_id: "manikandan",
      total_matches: recommendations.length,
      recommendations,
      profile_summary: {
        skills_count: 15,
        top_skills: ["python", "pytorch", "tensorflow", "scikit-learn", "fastapi"],
        experience_years: 0,
        preferred_types: ["full-time", "internship"],
        inferred_skills_count: 0
      }
    });
  } catch (error) {
    console.error("Recommendations Error:", error);
    return NextResponse.json({ error: "Failed to fetch recommendations" }, { status: 500 });
  }
}
