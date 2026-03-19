import logging
import urllib.parse

import requests
from bs4 import BeautifulSoup

from ..config import MAX_RESULTS_PER_SCRAPER, REQUEST_TIMEOUT, USER_AGENT
from ..models import Job, Preferences
from .base import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    name = "linkedin"
    BASE_URL = "https://www.linkedin.com/jobs/search"

    def search(self, preferences: Preferences) -> list[Job]:
        jobs = []
        try:
            params = {
                "keywords": preferences.job_title,
                "location": preferences.location,
                "sortBy": "DD",  # sort by date
                "position": "1",
                "pageNum": "0",
            }
            if preferences.remote_only:
                params["f_WT"] = "2"  # remote filter

            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }

            response = requests.get(
                self.BASE_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            job_cards = soup.select(
                "div.base-card, li.result-card, div.job-search-card"
            )

            for card in job_cards[:MAX_RESULTS_PER_SCRAPER]:
                try:
                    job = self._parse_card(card, preferences)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse LinkedIn card: {e}")
                    continue

        except Exception as e:
            logger.warning(f"LinkedIn search failed: {e}")

        logger.info(f"LinkedIn: found {len(jobs)} matching jobs")
        return jobs

    def _parse_card(self, card, pref: Preferences) -> Job | None:
        title_el = card.select_one(
            "h3.base-search-card__title, span.sr-only, h3.result-card__title"
        )
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        link_el = card.select_one("a.base-card__full-link, a.result-card__full-card-link")
        job_url = link_el["href"] if link_el and link_el.get("href") else ""
        job_id = ""
        if job_url:
            # Extract ID from URL like /jobs/view/123456789
            parts = job_url.rstrip("/").split("/")
            job_id = parts[-1] if parts else title[:50]
        if not job_id:
            job_id = card.get("data-entity-urn", title[:50])

        company_el = card.select_one(
            "h4.base-search-card__subtitle, a.result-card__subtitle-link"
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        loc_el = card.select_one(
            "span.job-search-card__location, span.result-card__meta"
        )
        location = loc_el.get_text(strip=True) if loc_el else ""

        is_remote = "remote" in (location + " " + title).lower()

        if pref.remote_only and not is_remote:
            return None

        return Job(
            source=self.name,
            external_id=str(job_id),
            title=title,
            company=company,
            location=location,
            url=job_url,
            remote=is_remote,
            description_snippet="",
            tags=[],
            preference_id=pref.id or 0,
        )
