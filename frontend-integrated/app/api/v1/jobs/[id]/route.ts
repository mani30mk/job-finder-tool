import { NextResponse } from "next/server";
import { turso } from "@/lib/turso";

export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    const result = await turso.execute({
      sql: "SELECT * FROM jobs WHERE job_id = ?",
      args: [params.id]
    });

    if (result.rows.length === 0) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    const row = result.rows[0];
    return NextResponse.json({
      job_id: String(row.job_id || ""),
      title: String(row.title || ""),
      company: String(row.company || ""),
      location: String(row.location || ""),
      employment_type: String(row.employment_type || ""),
      description: String(row.description || ""),
      requirements: String(row.requirements || ""),
      apply_url: String(row.apply_url || ""),
      source_platform: String(row.source_platform || ""),
      source_url: String(row.source_url || ""),
      posted_date: String(row.posted_date || "")
    });
  } catch (error) {
    console.error("Get Job Error:", error);
    return NextResponse.json({ error: "Failed to get job" }, { status: 500 });
  }
}
