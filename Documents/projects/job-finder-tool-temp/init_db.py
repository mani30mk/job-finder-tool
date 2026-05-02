"""Initialize the database. Run this first."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from database.db import init_db

if __name__ == "__main__":
    init_db()
    print("Database ready!")
