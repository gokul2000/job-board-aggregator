import logging

import requests
from bs4 import BeautifulSoup

from ..config import MAX_RESULTS_PER_SCRAPER, REQUEST_TIMEOUT, USER_AGENT
from ..models import Job, Preferences
from .base import BaseScraper

logger = logging.getLogger(__name__)


class GlassdoorScraper(BaseScraper):
    name = "glassdoor"
    BASE_URL = "https://www.glassdoor.com/Job/jobs.htm"

    def search(self, preferences: Preferences) -> list[Job]:
        jobs = []
        try:
            params = {
                "sc.keyword": preferences.job_title,
                "locT": "",
                "locId": "",
                "locKeyword": preferences.location,
                "jobType": "",
                "fromAge": "7",  # last 7 days
            }
            if preferences.remote_only:
                params["remoteWorkType"] = "1"

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
                "li.react-job-listing, div.jobCard, li[data-test='jobListing']"
            )

            for card in job_cards[:MAX_RESULTS_PER_SCRAPER]:
                try:
                    job = self._parse_card(card, preferences)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse Glassdoor card: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Glassdoor search failed: {e}")

        logger.info(f"Glassdoor: found {len(jobs)} matching jobs")
        return jobs

    def _parse_card(self, card, pref: Preferences) -> Job | None:
        title_el = card.select_one(
            "a.jobLink, a[data-test='job-link'], a.job-title"
        )
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        job_url = ""
        job_id = card.get("data-id", card.get("data-job-id", ""))
        if title_el and title_el.get("href"):
            href = title_el["href"]
            job_url = f"https://www.glassdoor.com{href}" if href.startswith("/") else href
        if not job_id:
            job_id = title[:50]

        company_el = card.select_one(
            "div.employerName, span.EmployerProfile, a[data-test='employer-short-name']"
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        loc_el = card.select_one(
            "span.loc, span[data-test='emp-location'], div.location"
        )
        location = loc_el.get_text(strip=True) if loc_el else ""

        sal_el = card.select_one(
            "span.salary, div[data-test='detailSalary'], span.css-18034rf"
        )
        salary_info = sal_el.get_text(strip=True) if sal_el else None

        is_remote = "remote" in (location + " " + title).lower()

        if pref.remote_only and not is_remote:
            return None

        if not self._matches_salary(salary_info, pref):
            return None

        return Job(
            source=self.name,
            external_id=str(job_id),
            title=title,
            company=company,
            location=location,
            url=job_url,
            salary_info=salary_info,
            remote=is_remote,
            description_snippet="",
            tags=[],
            preference_id=pref.id or 0,
        )
