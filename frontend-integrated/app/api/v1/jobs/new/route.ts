import { NextResponse } from "next/server";
import { turso } from "@/lib/turso";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get("limit") || "30");

  try {
    const result = await turso.execute({
      sql: `
        SELECT * FROM jobs 
        WHERE is_active = 1 AND is_new = 1
        ORDER BY 
            CASE WHEN source_platform = 'internshala' THEN 0 ELSE 1 END,
            CASE WHEN location LIKE '%india%' OR location LIKE '%bangalore%'
                      OR location LIKE '%bengaluru%' OR location LIKE '%chennai%'
                      OR location LIKE '%hyderabad%' OR location LIKE '%pune%'
                      OR location LIKE '%mumbai%' OR location LIKE '%delhi%'
                      OR location LIKE '%remote%'
                 THEN 0 ELSE 1 END,
            scraped_at DESC 
        LIMIT ?
      `,
      args: [limit]
    });

    const jobs = result.rows.map(row => ({
      job_id: String(row.job_id || ""),
      title: String(row.title || ""),
      company: String(row.company || ""),
      location: String(row.location || ""),
      employment_type: String(row.employment_type || ""),
      description: String(row.description || "").substring(0, 500),
      apply_url: String(row.apply_url || ""),
      source_platform: String(row.source_platform || ""),
      posted_date: String(row.posted_date || ""),
      scraped_at: String(row.scraped_at || "")
    }));

    return NextResponse.json({
      count: jobs.length,
      jobs
    });
  } catch (error) {
    console.error("New Jobs Error:", error);
    return NextResponse.json({ error: "Failed to fetch new jobs" }, { status: 500 });
  }
}
