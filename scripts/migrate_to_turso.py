import os
import sqlite3
import asyncio
from dotenv import load_dotenv
import libsql_client
from database.models import SCHEMA_SQL
from app_config.settings import DB_PATH

load_dotenv()

async def migrate_to_turso():
    url = os.environ.get("TURSO_DATABASE_URL")
    if url and url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not url or not token:
        print("Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN in .env")
        return

    print(f"Connecting to Turso: {url}")
    
    # 1. Connect to Turso
    async with libsql_client.create_client(url, auth_token=token) as client:
        # 2. Create Schema
        print("Creating schema on Turso...")
        try:
            await client.execute("DROP TABLE IF EXISTS jobs_fts")
            await client.execute("DROP TABLE IF EXISTS jobs")
        except Exception as e:
            pass
            
        statements = [s.strip() for s in SCHEMA_SQL.split(";") if s.strip()]
        for stmt in statements:
            try:
                await client.execute(stmt)
            except Exception as e:
                print(f"Error executing statement: {stmt}\nError: {e}")
        print("Schema created.")

        # 3. Read local data
        print("Reading local jobs.db...")
        if not DB_PATH.exists():
            print("No local jobs.db found.")
            return

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM jobs")
        rows = cursor.fetchall()
        print(f"Found {len(rows)} jobs in local database.")
        
        # 4. Insert data in batches
        print("Uploading data to Turso in batches...")
        batch_size = 500
        total_inserted = 0
        
        insert_sql = """
            INSERT OR IGNORE INTO jobs 
            (id, job_id, title, company, location, employment_type, description,
             requirements, apply_url, source_platform, source_url, posted_date, 
             scraped_at, is_active, is_new, gemini_score, gemini_reasons, gemini_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            stmts = []
            for row in batch:
                args = (
                    row['id'], row['job_id'], row['title'], row['company'], 
                    row['location'], row['employment_type'], row['description'],
                    row['requirements'], row['apply_url'], row['source_platform'], 
                    row['source_url'], row['posted_date'], row['scraped_at'], 
                    row['is_active'], row['is_new'], row['gemini_score'], 
                    row['gemini_reasons'], row['gemini_summary']
                )
                stmts.append(libsql_client.Statement(insert_sql, args))
                
            try:
                await client.batch(stmts)
                total_inserted += len(batch)
                print(f"Uploaded {total_inserted}/{len(rows)} jobs...")
            except Exception as e:
                print(f"Error inserting batch: {e}")
                
        print("Migration complete!")
        conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_to_turso())
