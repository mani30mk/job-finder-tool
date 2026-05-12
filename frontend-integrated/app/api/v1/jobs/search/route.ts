import { NextResponse } from "next/server";
import { turso } from "@/lib/turso";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") || "";
  const location = searchParams.get("location") || "";
  const employment_type = searchParams.get("employment_type") || "";
  const source = searchParams.get("source") || "";
  const limit = parseInt(searchParams.get("limit") || "50");
  const offset = parseInt(searchParams.get("offset") || "0");

  try {
    let sql = "SELECT * FROM jobs WHERE is_active = 1";
    const args: any[] = [];

    if (q) {
      sql += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)";
      args.push(`%${q}%`, `%${q}%`, `%${q}%`);
    }
    if (location) {
      sql += " AND location LIKE ?";
      args.push(`%${location}%`);
    }
    if (employment_type) {
      sql += " AND employment_type LIKE ?";
      args.push(`%${employment_type}%`);
    }
    if (source) {
      sql += " AND source_platform = ?";
      args.push(source);
    }

    sql += ` ORDER BY 
            CASE WHEN source_platform = 'internshala' THEN 0 ELSE 1 END,
            CASE WHEN location LIKE '%india%' OR location LIKE '%bangalore%'
                      OR location LIKE '%bengaluru%' OR location LIKE '%chennai%'
                      OR location LIKE '%hyderabad%' OR location LIKE '%pune%'
                      OR location LIKE '%mumbai%' OR location LIKE '%delhi%'
                      OR location LIKE '%remote%'
                 THEN 0 ELSE 1 END,
            posted_date DESC LIMIT ? OFFSET ?`;
    args.push(limit, offset);

    const result = await turso.execute({ sql, args });

    const jobs = result.rows.map(row => ({
      job_id: String(row.job_id || ""),
      title: String(row.title || ""),
      company: String(row.company || ""),
      location: String(row.location || ""),
      employment_type: String(row.employment_type || ""),
      description: String(row.description || "").substring(0, 300),
      apply_url: String(row.apply_url || ""),
      source_platform: String(row.source_platform || ""),
      posted_date: String(row.posted_date || "")
    }));

    return NextResponse.json({
      total: jobs.length,
      jobs,
      offset,
      limit
    });
  } catch (error) {
    console.error("Search Jobs Error:", error);
    return NextResponse.json({ error: "Failed to search jobs" }, { status: 500 });
  }
}
