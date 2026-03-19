import logging
import os

import requests

from ..config import APP_DIR, MAX_RESULTS_PER_SCRAPER, REQUEST_TIMEOUT
from ..models import Job, Preferences
from .base import BaseScraper

logger = logging.getLogger(__name__)


class AdzunaScraper(BaseScraper):
    name = "adzuna"
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    # Country code mapping for common locations
    COUNTRY_MAP = {
        "us": "us", "usa": "us", "united states": "us",
        "uk": "gb", "united kingdom": "gb", "england": "gb",
        "canada": "ca", "australia": "au", "india": "in",
        "germany": "de", "france": "fr", "netherlands": "nl",
        "brazil": "br", "singapore": "sg", "south africa": "za",
    }

    def _get_credentials(self) -> tuple[str, str] | None:
        app_id = os.environ.get("ADZUNA_APP_ID", "")
        app_key = os.environ.get("ADZUNA_APP_KEY", "")
        if app_id and app_key:
            return app_id, app_key

        cred_file = APP_DIR / "adzuna.conf"
        if cred_file.exists():
            import json
            try:
                data = json.loads(cred_file.read_text())
                return data["app_id"], data["app_key"]
            except Exception:
                pass
        return None

    def _detect_country(self, location: str) -> str:
        loc_lower = location.lower().strip()
        for keyword, code in self.COUNTRY_MAP.items():
            if keyword in loc_lower:
                return code
        return "us"  # default

    def search(self, preferences: Preferences) -> list[Job]:
        jobs = []
        creds = self._get_credentials()
        if not creds:
            logger.warning(
                "Adzuna: no API credentials found. Set ADZUNA_APP_ID and ADZUNA_APP_KEY "
                "env vars, or create ~/.jobhunt/adzuna.conf with {\"app_id\": ..., \"app_key\": ...}. "
                "Get free keys at https://developer.adzuna.com/"
            )
            return jobs

        app_id, app_key = creds
        country = self._detect_country(preferences.location)

        try:
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "what": preferences.job_title,
                "sort_by": "date",
                "results_per_page": min(MAX_RESULTS_PER_SCRAPER, 50),
                "content-type": "application/json",
            }

            if preferences.location.lower() not in ("remote", ""):
                params["where"] = preferences.location

            if preferences.salary_min:
                params["salary_min"] = preferences.salary_min
            if preferences.salary_max:
                params["salary_max"] = preferences.salary_max

            url = f"{self.BASE_URL}/{country}/search/1"
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            for item in results:
                try:
                    job = self._parse_listing(item, preferences)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse Adzuna listing: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Adzuna search failed: {e}")

        logger.info(f"Adzuna: found {len(jobs)} matching jobs")
        return jobs

    def _parse_listing(self, item: dict, pref: Preferences) -> Job | None:
        title = item.get("title", "")
        if not title:
            return None

        company_data = item.get("company", {})
        company = company_data.get("display_name", "Unknown") if isinstance(company_data, dict) else "Unknown"

        location_data = item.get("location", {})
        location_parts = []
        if isinstance(location_data, dict):
            for key in ("display_name", "area"):
                val = location_data.get(key)
                if isinstance(val, str) and val:
                    location_parts.append(val)
                elif isinstance(val, list):
                    location_parts.extend(val)
        location = ", ".join(location_parts) if location_parts else "Unknown"

        url = item.get("redirect_url", "")
        job_id = item.get("id", url)

        description = item.get("description", "")
        is_remote = "remote" in (title + " " + description + " " + location).lower()

        if pref.remote_only and not is_remote:
            return None

        # Build salary info from min/max
        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        salary_info = None
        if salary_min or salary_max:
            parts = []
            if salary_min:
                parts.append(f"${int(salary_min):,}")
            if salary_max:
                parts.append(f"${int(salary_max):,}")
            salary_info = " - ".join(parts)

        if not self._matches_salary(salary_info, pref):
            return None

        category_data = item.get("category", {})
        tags = []
        if isinstance(category_data, dict) and category_data.get("label"):
            tags.append(category_data["label"])

        return Job(
            source=self.name,
            external_id=str(job_id),
            title=title,
            company=company,
            location=location,
            url=url,
            salary_info=salary_info,
            remote=is_remote,
            description_snippet=description[:300] if description else "",
            tags=tags,
            preference_id=pref.id or 0,
        )
