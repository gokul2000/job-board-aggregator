import logging
from datetime import datetime

import requests

from ..config import REQUEST_TIMEOUT, USER_AGENT, MAX_RESULTS_PER_SCRAPER
from ..models import Job, Preferences
from .base import BaseScraper

logger = logging.getLogger(__name__)


class RemoteOKScraper(BaseScraper):
    name = "remoteok"
    API_URL = "https://remoteok.com/api"

    def search(self, preferences: Preferences) -> list[Job]:
        jobs = []
        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
            params = {}
            if preferences.job_title:
                params["tag"] = preferences.job_title.replace(" ", "-").lower()

            response = requests.get(
                self.API_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            # First item is metadata, skip it
            listings = data[1:] if len(data) > 1 else []

            for item in listings[:MAX_RESULTS_PER_SCRAPER]:
                try:
                    job = self._parse_listing(item, preferences)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse RemoteOK listing: {e}")
                    continue

        except Exception as e:
            logger.warning(f"RemoteOK search failed: {e}")

        logger.info(f"RemoteOK: found {len(jobs)} matching jobs")
        return jobs

    def _parse_listing(self, item: dict, pref: Preferences) -> Job | None:
        title = item.get("position", "")
        company = item.get("company", "")
        description = item.get("description", "")
        tags = item.get("tags", [])
        salary_info = item.get("salary", "")
        url = item.get("url", "")
        slug = item.get("slug", item.get("id", ""))
        location = item.get("location", "Remote")

        if not title:
            return None

        # Build searchable text
        search_text = f"{title} {description} {' '.join(tags)}"

        # Check title relevance
        title_words = pref.job_title.lower().split()
        title_lower = title.lower()
        if not any(w in title_lower or w in search_text.lower() for w in title_words):
            return None

        # Check salary match
        if not self._matches_salary(salary_info, pref):
            return None

        if url and not url.startswith("http"):
            url = f"https://remoteok.com{url}"

        return Job(
            source=self.name,
            external_id=str(slug),
            title=title,
            company=company,
            location=location or "Remote",
            url=url,
            salary_info=salary_info if salary_info else None,
            remote=True,
            description_snippet=description[:300] if description else "",
            tags=tags[:10] if tags else [],
            preference_id=pref.id or 0,
        )
