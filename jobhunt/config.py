import os
from pathlib import Path

APP_DIR = Path.home() / ".jobhunt"
DB_PATH = APP_DIR / "jobhunt.db"
EMAIL_CONFIG_PATH = APP_DIR / "email.conf"
LOG_PATH = APP_DIR / "jobhunt.log"

DEFAULT_SEARCH_INTERVAL = 60  # minutes
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 15  # seconds
MAX_RESULTS_PER_SCRAPER = 50
