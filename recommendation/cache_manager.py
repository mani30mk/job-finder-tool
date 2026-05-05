"""Caching layer for parsed profiles and job embeddings."""
import sqlite3
import json
import hashlib
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


class CacheManager:
    """SQLite-based cache for profiles, embeddings, and job data."""

    def __init__(self, cache_path: str = ".jobhunter_cache.db"):
        self.cache_path = cache_path
        self._init_db()

    def _init_db(self):
        """Initialize cache tables."""
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile_cache (
                file_hash TEXT PRIMARY KEY,
                profile_json TEXT,
                created_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                text_hash TEXT PRIMARY KEY,
                embedding BLOB,
                model_name TEXT,
                created_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_cache (
                job_id TEXT PRIMARY KEY,
                job_json TEXT,
                source TEXT,
                created_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                results_json TEXT,
                created_at TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:32]

    def get_profile(self, file_path: str) -> Optional[Dict]:
        """Get cached profile for a file."""
        try:
            file_content = Path(file_path).read_text(errors="ignore")
        except Exception:
            return None
        file_hash = self._hash(file_content)
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT profile_json FROM profile_cache WHERE file_hash = ?",
            (file_hash,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])
        return None

    def save_profile(self, file_path: str, profile: Any):
        """Cache a parsed profile."""
        try:
            file_content = Path(file_path).read_text(errors="ignore")
        except Exception:
            return
        file_hash = self._hash(file_content)
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()

        from dataclasses import asdict
        profile_dict = asdict(profile) if hasattr(profile, "__dataclass_fields__") else profile

        cursor.execute(
            "INSERT OR REPLACE INTO profile_cache VALUES (?, ?, ?)",
            (file_hash, json.dumps(profile_dict), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_embedding(self, text: str, model_name: str) -> Optional[List[float]]:
        """Get cached embedding."""
        text_hash = self._hash(text + model_name)
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT embedding FROM embedding_cache WHERE text_hash = ?",
            (text_hash,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return pickle.loads(row[0])
        return None

    def save_embedding(self, text: str, model_name: str, embedding: List[float]):
        """Cache an embedding vector."""
        text_hash = self._hash(text + model_name)
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR REPLACE INTO embedding_cache VALUES (?, ?, ?, ?)",
            (text_hash, pickle.dumps(embedding), model_name, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get cached job."""
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        cursor.execute("SELECT job_json FROM job_cache WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return None

    def save_job(self, job_id: str, job: Dict, source: str = "web"):
        """Cache a job."""
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO job_cache VALUES (?, ?, ?, ?)",
            (job_id, json.dumps(job), source, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def clear_expired(self, days: int = 7):
        """Clear cache entries older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()

        for table in ["profile_cache", "embedding_cache", "job_cache", "search_cache"]:
            cursor.execute(f"DELETE FROM {table} WHERE created_at < ?", (cutoff,))

        conn.commit()
        conn.close()
