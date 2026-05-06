"""Global configuration for job-hunter."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "jobs.db"
SESSION_DIR = BASE_DIR / "session_data"
LOGS_DIR = BASE_DIR / "logs"

# ─── Search preferences — tuned for India fresher/intern ──────────────────────
KEYWORDS = [
    # ML/AI internships (your core strength)
    "machine learning intern",
    "deep learning intern",
    "ai intern",
    "data science intern",
    "computer vision intern",
    "nlp intern",
    "ml research intern",
    "ai research intern",
    "research intern machine learning",
    # Software internships
    "software engineer intern",
    "sde intern",
    "software developer intern",
    "backend intern",
    "python intern",
    "developer intern",
    "software trainee",
    # Entry level / fresher
    "fresher software engineer",
    "junior ml engineer",
    "graduate engineer trainee",
    "associate software engineer",
    "entry level python",
    "campus hiring",
    "off campus hiring",
]

LOCATIONS = [
    "India",
    "Remote",
    "Work from home",
    "WFH",
    "Bangalore",
    "Bengaluru",
    "Chennai",
    "Hyderabad",
    "Mumbai",
    "Pune",
    "Delhi",
    "Noida",
    "Gurugram",
    "Gurgaon",
    "Tamil Nadu",
    "Karnataka",
    "Telangana",
]

JOB_TYPES = ["Internship", "Full-time", "Entry Level", "Fresher"]

# Scraping limits
LINKEDIN_MAX_PAGES = 3
WORKDAY_MAX_JOBS = 50
REQUEST_DELAY = (8, 15)

# Alerts
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")

# Ollama config
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "mistral"
