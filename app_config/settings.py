"""Global configuration for job-hunter."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "jobs.db"
SESSION_DIR = BASE_DIR / "session_data"
LOGS_DIR = BASE_DIR / "logs"

# Search preferences (customize these)
KEYWORDS = ["software engineer", "backend engineer", "full stack", "devops", "data engineer"]
LOCATIONS = ["India", "Remote", "Bangalore", "Hyderabad", "Mumbai", "Pune"]
JOB_TYPES = ["Full-time", "Internship"]  # or None for all

# Scraping limits (keep low to avoid blocks)
LINKEDIN_MAX_PAGES = 3
WORKDAY_MAX_JOBS = 50
REQUEST_DELAY = (8, 15)  # seconds between requests

# Discord webhook for alerts (optional)
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")

# Ollama config
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "mistral"
