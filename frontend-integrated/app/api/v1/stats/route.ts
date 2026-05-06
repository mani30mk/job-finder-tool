import { NextResponse } from "next/server";
import { turso } from "@/lib/turso";

export async function GET() {
  try {
    const totalResult = await turso.execute("SELECT COUNT(*) as total FROM jobs");
    const activeResult = await turso.execute("SELECT COUNT(*) as active FROM jobs WHERE is_active = 1");
    const newResult = await turso.execute("SELECT COUNT(*) as new_jobs FROM jobs WHERE is_new = 1");
    
    const sourcesResult = await turso.execute(`
      SELECT source_platform, COUNT(*) as count 
      FROM jobs 
      WHERE is_active = 1 
      GROUP BY source_platform 
      ORDER BY count DESC
    `);
    
    const totalJobs = Number(totalResult.rows[0].total) || 0;
    const activeJobs = Number(activeResult.rows[0].active) || 0;
    
    const sources = sourcesResult.rows.map(row => ({
      name: String(row.source_platform),
      count: Number(row.count)
    }));

    return NextResponse.json({
      total_jobs: totalJobs,
      active_jobs: activeJobs,
      total_sources: sources.length,
      top_sources: sources,
      last_scraped: new Date().toISOString()
    });
  } catch (error) {
    console.error("Stats Error:", error);
    return NextResponse.json({ error: "Failed to fetch stats" }, { status: 500 });
  }
}
