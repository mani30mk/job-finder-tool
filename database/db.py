"""Database connection and CRUD operations."""
import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional, Set
from pathlib import Path

from app_config.settings import DB_PATH
from database.models import SCHEMA_SQL

import os
import libsql_experimental as libsql
from dotenv import load_dotenv

load_dotenv()

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "").strip().strip("\"'")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "").strip().strip("\"'")


def init_db():
    """Initialize database with schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TURSO_URL:
        print(f"[DB] Using Turso cloud database: {TURSO_URL[:30]}***")
        return
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    print(f"[DB] Initialized local sqlite at {DB_PATH}")


@contextmanager
def get_conn():
    """Returns a local sqlite connection or a wrapper around libsql_experimental for Turso."""
    if TURSO_URL:

        class RowMock:
            """Mimics sqlite3.Row so callers can use row['col'] or row[0]."""
            def __init__(self, cols, row):
                self.cols = list(cols)
                self.row = list(row)
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
                # libsql_experimental uses https:// internally — pass libsql:// URL as-is
                self.conn = libsql.connect(
                    database=TURSO_URL,
                    auth_token=TURSO_TOKEN,
                    sync_url=TURSO_URL,
                )

            def execute(self, sql, params=()):
                cur = self.conn.execute(sql, params)
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = [RowMock(cols, r) for r in (cur.fetchall() or [])]
                return ResultSet(rows)

            def executemany(self, sql, params_list):
                for p in params_list:
                    self.conn.execute(sql, p)

            def executescript(self, sql):
                self.conn.executescript(sql)

            def commit(self):
                self.conn.commit()

            def close(self):
                pass  # libsql_experimental manages its own lifecycle

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
                err_msg = str(e).lower()
                if any(k in err_msg for k in ("unique", "constraint", "duplicate", "conflict")):
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
        saved = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_saved = 1").fetchone()[0]
        platforms = conn.execute(
            "SELECT source_platform, COUNT(*) as cnt FROM jobs GROUP BY source_platform"
        ).fetchall()
        return {
            "total": total,
            "active": active,
            "new": new,
            "saved": saved,
            "by_platform": {r["source_platform"]: r["cnt"] for r in platforms}
        }


def delete_old_jobs(days: int = 30) -> int:
    """Permanently DELETE jobs older than N days, EXCEPT saved ones."""
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE scraped_at < ? AND is_saved = 0",
            (cutoff,)
        ).fetchone()
        count = result[0] if result else 0
        if count > 0:
            conn.execute(
                "DELETE FROM jobs WHERE scraped_at < ? AND is_saved = 0",
                (cutoff,)
            )
            conn.commit()
        return count


def toggle_save_job(job_id: str) -> bool:
    """Toggle is_saved for a job. Returns new saved state."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT is_saved FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return False
        new_state = 0 if row[0] else 1
        conn.execute(
            "UPDATE jobs SET is_saved = ? WHERE job_id = ?",
            (new_state, job_id)
        )
        conn.commit()
        return bool(new_state)


def set_job_saved(job_id: str, saved: bool = True) -> bool:
    """Set is_saved for a job. Returns True if job existed."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET is_saved = ? WHERE job_id = ?",
            (1 if saved else 0, job_id)
        )
        conn.commit()
        return True


def get_saved_jobs(limit: int = 200) -> list:
    """Get all saved jobs."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE is_saved = 1 ORDER BY scraped_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return rows