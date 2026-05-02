"""Configuration loader — reads API keys from .env file or environment variables.

Usage:
    from app_config.config import Config

    # Access any key
    api_key = Config.SERPAPI_KEY

    # Check if key is set
    if Config.has_key("SERPAPI_KEY"):
        scraper = SerpApiScraper(api_key=Config.SERPAPI_KEY)

    # Get all job API keys
    keys = Config.get_job_api_keys()
"""
import os
from pathlib import Path
from typing import Dict, Optional


class Config:
    """Central configuration manager."""

    # --- API Keys ---
    SERPAPI_KEY: str = ""
    RAPIDAPI_KEY: str = ""      # JSearch
    THEIRSTACK_KEY: str = ""
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""

    # --- LinkedIn (optional, local only) ---
    LINKEDIN_EMAIL: str = ""
    LINKEDIN_PASSWORD: str = ""

    # --- Scraping Settings ---
    REQUEST_DELAY: tuple = (1, 3)           # Min, max seconds between requests
    LINKEDIN_MAX_PAGES: int = 5
    DEFAULT_QUERY: str = "software engineer"
    DEFAULT_LOCATION: str = ""
    DEFAULT_COUNTRY: str = "us"

    # --- Database ---
    DB_PATH: str = "jobs.db"

    # --- Session ---
    SESSION_DIR: str = "session_data"

    _loaded: bool = False

    @classmethod
    def load(cls, env_file: str = ".env") -> None:
        """Load configuration from .env file and environment variables.

        Priority: Environment variables > .env file > defaults
        """
        if cls._loaded:
            return

        # Try to load python-dotenv if available
        try:
            from dotenv import load_dotenv
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(env_path)
                print(f"[Config] Loaded .env from {env_path.absolute()}")
            else:
                print(f"[Config] .env file not found at {env_path.absolute()}")
                print(f"[Config] Copy .env.example -> .env and fill in your API keys")
        except ImportError:
            print("[Config] python-dotenv not installed. Using os.environ only.")
            print("[Config] Install: pip install python-dotenv")

        # Load all keys from environment (set by .env or manual export)
        cls.SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
        cls.RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
        cls.THEIRSTACK_KEY = os.getenv("THEIRSTACK_KEY", "")
        cls.ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
        cls.ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
        cls.LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
        cls.LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

        cls._loaded = True
        cls._print_status()

    @classmethod
    def _print_status(cls) -> None:
        """Print which API keys are configured."""
        print("\n" + "=" * 50)
        print("API Key Status")
        print("=" * 50)

        apis = [
            ("SerpApi (Google Jobs)", cls.SERPAPI_KEY, "100 free/month"),
            ("JSearch (RapidAPI)", cls.RAPIDAPI_KEY, "200 free/month"),
            ("TheirStack", cls.THEIRSTACK_KEY, "200 free/month"),
            ("Adzuna", cls.ADZUNA_APP_KEY and cls.ADZUNA_APP_ID, "100 free/day"),
            ("LinkedIn", cls.LINKEDIN_EMAIL, "Browser-based"),
        ]

        for name, key, quota in apis:
            status = "✅ Configured" if key else "❌ Not set"
            print(f"   {name:<25} {status:<15} ({quota})")

        print("=" * 50)

    @classmethod
    def has_key(cls, key_name: str) -> bool:
        """Check if an API key is set."""
        return bool(getattr(cls, key_name, ""))

    @classmethod
    def get_job_api_keys(cls) -> Dict[str, str]:
        """Get all configured job API keys as a dictionary."""
        return {
            "serpapi": cls.SERPAPI_KEY,
            "jsearch": cls.RAPIDAPI_KEY,
            "theirstack": cls.THEIRSTACK_KEY,
            "adzuna_id": cls.ADZUNA_APP_ID,
            "adzuna_key": cls.ADZUNA_APP_KEY,
        }

    @classmethod
    def get_active_apis(cls) -> list:
        """Return list of APIs that have keys configured."""
        active = []
        if cls.SERPAPI_KEY:
            active.append("serpapi")
        if cls.RAPIDAPI_KEY:
            active.append("jsearch")
        if cls.THEIRSTACK_KEY:
            active.append("theirstack")
        if cls.ADZUNA_APP_ID and cls.ADZUNA_APP_KEY:
            active.append("adzuna")
        return active
