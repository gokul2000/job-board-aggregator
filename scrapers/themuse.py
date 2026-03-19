import logging

import requests

from ..config import MAX_RESULTS_PER_SCRAPER, REQUEST_TIMEOUT
from ..models import Job, Preferences
from .base import BaseScraper

logger = logging.getLogger(__name__)


class TheMuseScraper(BaseScraper):
    name = "themuse"
    API_URL = "https://www.themuse.com/api/public/jobs"

    def search(self, preferences: Preferences) -> list[Job]:
        jobs = []
        try:
            params = {
                "page": 0,
            }
            if preferences.location and preferences.location.lower() != "remote":
                params["location"] = preferences.location
            if preferences.remote_only:
                params["location"] = "Flexible / Remote"

            # The Muse doesn't have a direct keyword search param in the same way,
            # but we can filter by category or use the page parameter
            # We'll fetch and filter client-side by title match
            params["page"] = 0

            all_listings = []
            for page in range(3):  # fetch up to 3 pages
                params["page"] = page
                response = requests.get(
                    self.API_URL, params=params, timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                if not results:
                    break
                all_listings.extend(results)

            for item in all_listings[:MAX_RESULTS_PER_SCRAPER]:
                try:
                    job = self._parse_listing(item, preferences)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse The Muse listing: {e}")
                    continue

        except Exception as e:
            logger.warning(f"The Muse search failed: {e}")

        logger.info(f"The Muse: found {len(jobs)} matching jobs")
        return jobs

    def _parse_listing(self, item: dict, pref: Preferences) -> Job | None:
        title = item.get("name", "")
        if not title:
            return None

        # Check title relevance
        title_words = pref.job_title.lower().split()
        search_text = title.lower()
        if not any(w in search_text for w in title_words):
            return None

        company_data = item.get("company", {})
        company = company_data.get("name", "Unknown") if isinstance(company_data, dict) else "Unknown"

        locations = item.get("locations", [])
        location_str = ", ".join(
            loc.get("name", "") for loc in locations if isinstance(loc, dict)
        ) if locations else "Unknown"

        is_remote = "remote" in location_str.lower() or "flexible" in location_str.lower()

        if pref.remote_only and not is_remote:
            return None

        job_id = item.get("id", "")
        short_name = item.get("short_name", "")
        url = f"https://www.themuse.com/jobs/{company.lower().replace(' ', '-')}/{short_name}" if short_name else item.get("refs", {}).get("landing_page", "")

        categories = item.get("categories", [])
        tags = [cat.get("name", "") for cat in categories if isinstance(cat, dict)]

        levels = item.get("levels", [])
        level_names = [lv.get("name", "").lower() for lv in levels if isinstance(lv, dict)]

        if pref.experience_level != "any":
            level_map = {
                "entry": ["internship", "entry level", "entry"],
                "mid": ["mid level", "mid"],
                "senior": ["senior level", "senior", "management"],
            }
            expected = level_map.get(pref.experience_level, [])
            if expected and not any(e in " ".join(level_names) for e in expected):
                return None

        snippet = item.get("contents", "")
        if snippet:
            # Strip HTML tags from snippet
            import re
            snippet = re.sub(r"<[^>]+>", "", snippet)[:300]

        return Job(
            source=self.name,
            external_id=str(job_id),
            title=title,
            company=company,
            location=location_str,
            url=url,
            remote=is_remote,
            description_snippet=snippet,
            tags=tags,
            preference_id=pref.id or 0,
        )
