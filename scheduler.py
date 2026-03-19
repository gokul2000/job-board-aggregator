import logging
import signal
import time

from .db import Database
from .models import Preferences
from .notifier import ConsoleNotifier, EmailNotifier
from .search import SearchEngine

logger = logging.getLogger(__name__)


def run_periodic(engine: SearchEngine, db: Database, interval_minutes: int = 60):
    console = ConsoleNotifier(db)
    email = EmailNotifier(db)

    running = True

    def handle_signal(signum, frame):
        nonlocal running
        print("\nStopping scheduler...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"Scheduler started. Searching every {interval_minutes} minute(s).")
    print("Press Ctrl+C to stop.\n")

    while running:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running search...")
        try:
            results = engine.run_all()
            for pref_id, new_jobs in results.items():
                if new_jobs:
                    console.notify(new_jobs)
                    pref = db.get_preference(pref_id)
                    if pref and pref.notify_email and email.is_configured():
                        email.notify(new_jobs, pref.notify_email)
                else:
                    pref = db.get_preference(pref_id)
                    name = pref.job_title if pref else f"#{pref_id}"
                    print(f"  No new jobs for '{name}'")
        except Exception as e:
            logger.error(f"Search cycle failed: {e}")

        if not running:
            break

        print(f"\nNext search in {interval_minutes} minute(s)...\n")
        for _ in range(interval_minutes * 60):
            if not running:
                break
            time.sleep(1)

    print("Scheduler stopped.")
