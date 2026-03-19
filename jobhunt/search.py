import logging

from .db import Database
from .models import Job
from .scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class SearchEngine:
    def __init__(self, db: Database, scrapers: list[BaseScraper]):
        self.db = db
        self.scrapers = scrapers

    def run_search(self, preference_id: int) -> list[Job]:
        pref = self.db.get_preference(preference_id)
        if not pref:
            logger.error(f"Preference {preference_id} not found")
            return []

        all_jobs = []
        for scraper in self.scrapers:
            try:
                jobs = scraper.search(pref)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning(f"Scraper {scraper.name} failed: {e}")

        new_count = self.db.save_jobs(all_jobs)
        logger.info(f"Search complete: {len(all_jobs)} total, {new_count} new")
        return self.db.get_unnotified_jobs(preference_id)

    def run_all(self) -> dict[int, list[Job]]:
        results = {}
        for pref in self.db.get_preferences():
            results[pref.id] = self.run_search(pref.id)
        return results
