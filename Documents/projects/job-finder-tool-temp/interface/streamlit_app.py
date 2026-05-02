"""Streamlit web dashboard for job search."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import sqlite3
import streamlit as st
from database.db import DB_PATH

st.set_page_config(
    page_title="Job Hunter",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title(" Universal Job Search Dashboard")
st.caption("Personal job aggregator - zero budget, full coverage")

# Sidebar filters
st.sidebar.header("Filters")
search_query = st.sidebar.text_input("Keywords", "software engineer")
location = st.sidebar.text_input("Location", "India")
job_type = st.sidebar.selectbox(
    "Job Type",
    ["All", "Full-time", "Internship", "Contract", "Part-time"]
)
platform_filter = st.sidebar.multiselect(
    "Platforms",
    ["greenhouse", "lever", "ashby", "unstop", "internshala", 
     "hackernews", "linkedin", "workday", "custom"],
    default=[]
)
limit = st.sidebar.slider("Results", 10, 200, 50)

# Build query
conn = sqlite3.connect(DB_PATH)
params = []
conditions = ["j.is_active = 1"]

if search_query:
    conditions.append("jobs_fts MATCH ?")
    params.append(search_query)

query = f"""
    SELECT j.* FROM jobs j
    JOIN jobs_fts fts ON j.id = fts.rowid
    WHERE {" AND ".join(conditions)}
"""

if location:
    query += " AND j.location LIKE ?"
    params.append(f"%{location}%")

if job_type != "All":
    query += " AND j.employment_type = ?"
    params.append(job_type)

if platform_filter:
    placeholders = ",".join(["?"] * len(platform_filter))
    query += f" AND j.source_platform IN ({placeholders})"
    params.extend(platform_filter)

query += " ORDER BY j.scraped_at DESC LIMIT ?"
params.append(limit)

rows = conn.execute(query, params).fetchall()
conn.close()

st.subheader(f"Found {len(rows)} jobs")

# Display jobs
for row in rows:
    with st.expander(f"{row[1]} at {row[2]} — {row[3] or 'Remote'}"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Type:** {row[4] or 'Unknown'}")
            st.write(f"**Platform:** {row[8]}")
        with col2:
            st.write(f"**Posted:** {row[10] or 'Recently'}")
            st.write(f"**Scraped:** {row[11][:10]}")
        with col3:
            st.link_button("Apply Now", row[7])

        if row[5]:
            st.write("**Description:**")
            st.write(str(row[5])[:800] + ("..." if len(str(row[5])) > 800 else ""))

        if row[6]:
            st.write("**Requirements:**")
            st.write(str(row[6])[:500] + ("..." if len(str(row[6])) > 500 else ""))

# Footer
st.divider()
st.caption("Built with Scrapy + Playwright + Ollama + SQLite | Runs locally | Zero cost")
