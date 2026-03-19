import logging

import requests

from ..config import MAX_RESULTS_PER_SCRAPER, REQUEST_TIMEOUT
from ..models import Job, Preferences
from .base import BaseScraper

logger = logging.getLogger(__name__)


class ArbeitnowScraper(BaseScraper):
    name = "arbeitnow"
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def search(self, preferences: Preferences) -> list[Job]:
        jobs = []
        try:
            all_listings = []
            for page in range(1, 4):  # fetch up to 3 pages
                params = {"page": page}
                response = requests.get(
                    self.API_URL, params=params, timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("data", [])
                if not results:
                    break
                all_listings.extend(results)

            for item in all_listings[:MAX_RESULTS_PER_SCRAPER]:
                try:
                    job = self._parse_listing(item, preferences)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse Arbeitnow listing: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Arbeitnow search failed: {e}")

        logger.info(f"Arbeitnow: found {len(jobs)} matching jobs")
        return jobs

    def _parse_listing(self, item: dict, pref: Preferences) -> Job | None:
        title = item.get("title", "")
        if not title:
            return None

        # Check title relevance
        title_words = pref.job_title.lower().split()
        search_text = (title + " " + item.get("description", "")).lower()
        if not any(w in search_text for w in title_words):
            return None

        company = item.get("company_name", "Unknown")
        location = item.get("location", "Unknown")
        url = item.get("url", "")
        slug = item.get("slug", "")
        job_id = slug or url or title[:50]

        is_remote = item.get("remote", False) or "remote" in location.lower()

        if pref.remote_only and not is_remote:
            return None

        tags = item.get("tags", [])
        if isinstance(tags, list):
            tags = [str(t) for t in tags[:10]]
        else:
            tags = []

        # Check skill match
        if pref.skills:
            combined = (title + " " + " ".join(tags) + " " + item.get("description", "")).lower()
            if self._skill_match_score(combined, pref.skills) == 0:
                return None

        description = item.get("description", "")
        if description:
            import re
            description = re.sub(r"<[^>]+>", "", description)[:300]

        return Job(
            source=self.name,
            external_id=str(job_id),
            title=title,
            company=company,
            location=location,
            url=url,
            remote=is_remote,
            description_snippet=description,
            tags=tags,
            preference_id=pref.id or 0,
        )
