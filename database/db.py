"""Database connection and CRUD operations."""
import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional, Set
from pathlib import Path

from app_config.settings import DB_PATH
from database.models import SCHEMA_SQL


import os
import libsql_client
from dotenv import load_dotenv

load_dotenv()

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "").strip()
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
# Keep the native libsql:// scheme — the Python libsql_client sync client
# requires it (https:// is NOT supported and causes 'Unsupported URL scheme' errors).
# Do NOT replace libsql:// with https:// here.

def init_db():
    """Initialize database with schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TURSO_URL:
        # Turso uses a cloud db, schema is already created by migration script.
        # So we skip local schema creation for Turso.
        print(f"[DB] Using Turso cloud database: {TURSO_URL}")
        return

    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    print(f"[DB] Initialized local sqlite at {DB_PATH}")

@contextmanager
def get_conn():
    """Returns a local sqlite connection or a fake sqlite connection wrapping libsql sync client."""
    if TURSO_URL:
        # Validate the URL looks sane before handing it to libsql_client
        if not TURSO_URL.startswith(("libsql://", "wss://", "ws://", "file:")):
            raise ValueError(
                f"[DB] TURSO_DATABASE_URL has an unsupported scheme: '{TURSO_URL[:30]}...'. "
                "It must start with 'libsql://' (e.g. libsql://<db>.turso.io). "
                "Check that the TURSO_DATABASE_URL secret is set correctly in GitHub."
            )

        class RowMock:
            """Mimics sqlite3.Row so callers can use row['col'] or row[0]."""
            def __init__(self, cols, row):
                self.cols = cols
                self.row = row
            def __getitem__(self, key):
                if isinstance(key, int):
                    return self.row[key]
                return self.row[self.cols.index(key)]
            def keys(self):
                return self.cols

        class ResultSet:
            """Mimics a sqlite3 cursor result so .fetchall() and .fetchone() work."""
            def __init__(self, rows):
                self._rows = rows
            def fetchall(self):
                return self._rows
            def fetchone(self):
                return self._rows[0] if self._rows else None
            def __iter__(self):
                return iter(self._rows)
            def __len__(self):
                return len(self._rows)
            def __getitem__(self, idx):
                return self._rows[idx]

        class TursoWrapper:
            def __init__(self):
                self.client = libsql_client.create_client_sync(TURSO_URL, auth_token=TURSO_TOKEN)
            def execute(self, sql, params=()):
                res = self.client.execute(sql, params)
                rows = [RowMock(res.columns, r) for r in res.rows]
                return ResultSet(rows)
            def executemany(self, sql, params_list):
                stmts = [libsql_client.Statement(sql, p) for p in params_list]
                self.client.batch(stmts)
            def commit(self):
                pass
            def close(self):
                self.client.close()
                
        wrapper = TursoWrapper()
        try:
            yield wrapper
        finally:
            wrapper.close()
    else:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def insert_jobs(jobs: List[Dict]) -> int:
    """Insert jobs, skipping duplicates. Returns count inserted."""
    if not jobs:
        return 0

    inserted = 0
    with get_conn() as conn:
        for job in jobs:
            try:
                conn.execute("""
                    INSERT INTO jobs 
                    (job_id, title, company, location, employment_type, description,
                     requirements, apply_url, source_platform, source_url, posted_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job["job_id"], job["title"], job["company"],
                    job.get("location", ""), job.get("employment_type", ""),
                    job.get("description", ""), job.get("requirements", ""),
                    job["apply_url"], job["source_platform"],
                    job.get("source_url", ""), job.get("posted_date", "")
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                pass  # Duplicate job_id (local sqlite)
            except Exception as e:
                # Turso/libsql raises a generic exception for constraint violations
                err_msg = str(e).lower()
                if "unique" in err_msg or "constraint" in err_msg or "duplicate" in err_msg or "conflict" in err_msg:
                    pass  # Duplicate job_id (Turso)
                else:
                    raise
        conn.commit()
    return inserted


def get_existing_job_ids() -> Set[str]:
    """Get all existing job_ids for deduplication."""
    with get_conn() as conn:
        rows = conn.execute("SELECT job_id FROM jobs").fetchall()
        return {r["job_id"] for r in rows}


def search_jobs(
    keywords: str,
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50
) -> List[sqlite3.Row]:
    """Full-text search jobs."""
    with get_conn() as conn:
        query = """
            SELECT j.* FROM jobs j
            JOIN jobs_fts fts ON j.id = fts.rowid
            WHERE jobs_fts MATCH ? AND j.is_active = 1
        """
        params = [keywords]

        if location:
            query += " AND j.location LIKE ?"
            params.append(f"%{location}%")
        if job_type:
            query += " AND j.employment_type = ?"
            params.append(job_type)

        query += " ORDER BY j.scraped_at DESC LIMIT ?"
        params.append(limit)

        return conn.execute(query, params).fetchall()


def get_new_jobs(keywords: List[str], since_hours: int = 24) -> List[sqlite3.Row]:
    """Get new jobs matching keywords."""
    from datetime import datetime, timedelta
    since = (datetime.now() - timedelta(hours=since_hours)).isoformat()

    with get_conn() as conn:
        conditions = " OR ".join([f"jobs_fts MATCH ?" for _ in keywords])
        query = f"""
            SELECT j.* FROM jobs j
            JOIN jobs_fts fts ON j.id = fts.rowid
            WHERE ({conditions})
            AND j.is_new = 1
            AND j.scraped_at > ?
            LIMIT 20
        """
        params = keywords + [since]
        return conn.execute(query, params).fetchall()


def mark_notified(job_ids: List[str]):
    """Mark jobs as no longer new."""
    with get_conn() as conn:
        conn.executemany("UPDATE jobs SET is_new = 0 WHERE job_id = ?",
                        [(jid,) for jid in job_ids])
        conn.commit()


def deactivate_old_jobs(days: int = 14):
    """Mark jobs older than N days as inactive."""
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE jobs SET is_active = 0 WHERE scraped_at < ?", (cutoff,))
        conn.commit()


def get_stats() -> Dict:
    """Get database statistics."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0]
        new = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_new = 1").fetchone()[0]
        platforms = conn.execute(
            "SELECT source_platform, COUNT(*) as cnt FROM jobs GROUP BY source_platform"
        ).fetchall()
        return {
            "total": total,
            "active": active,
            "new": new,
            "by_platform": {r["source_platform"]: r["cnt"] for r in platforms}
        }
