"""SQLite schema definitions."""

SCHEMA_SQL = """
-- Main jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    employment_type TEXT,
    description TEXT,
    requirements TEXT,
    apply_url TEXT NOT NULL,
    source_platform TEXT NOT NULL,
    source_url TEXT,
    posted_date TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    is_new BOOLEAN DEFAULT 1
);

-- Full-text search virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
    title, company, location, description,
    content='jobs',
    content_rowid='id'
);

-- Keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
    INSERT INTO jobs_fts(rowid, title, company, location, description)
    VALUES (new.id, new.title, new.company, new.location, new.description);
END;

CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company, location, description)
    VALUES ('delete', old.id, old.title, old.company, old.location, old.description);
END;

CREATE TRIGGER IF NOT EXISTS jobs_au AFTER UPDATE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company, location, description)
    VALUES ('delete', old.id, old.title, old.company, old.location, old.description);
    INSERT INTO jobs_fts(rowid, title, company, location, description)
    VALUES (new.id, new.title, new.company, new.location, new.description);
END;

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(source_platform);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_new ON jobs(is_new);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs(scraped_at);
"""
