import logging
import urllib.parse

import requests
from bs4 import BeautifulSoup

from ..config import MAX_RESULTS_PER_SCRAPER, REQUEST_TIMEOUT, USER_AGENT
from ..models import Job, Preferences
from .base import BaseScraper

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    name = "indeed"
    BASE_URL = "https://www.indeed.com/jobs"

    def search(self, preferences: Preferences) -> list[Job]:
        jobs = []
        try:
            params = {
                "q": preferences.job_title,
                "l": preferences.location if not preferences.remote_only else "remote",
                "sort": "date",
            }
            if preferences.salary_min:
                params["salary"] = str(preferences.salary_min)

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
            job_cards = soup.select("div.job_seen_beacon, div.jobsearch-ResultsList > div, div.result")

            for card in job_cards[:MAX_RESULTS_PER_SCRAPER]:
                try:
                    job = self._parse_card(card, preferences)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse Indeed card: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Indeed search failed: {e}")

        logger.info(f"Indeed: found {len(jobs)} matching jobs")
        return jobs

    def _parse_card(self, card, pref: Preferences) -> Job | None:
        # Title
        title_el = card.select_one("h2.jobTitle a, h2.jobTitle span, a.jcs-JobTitle")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        # Link
        link_el = card.select_one("a[href*='/rc/clk'], a[href*='/viewjob'], h2.jobTitle a, a.jcs-JobTitle")
        job_url = ""
        job_id = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            job_url = f"https://www.indeed.com{href}" if href.startswith("/") else href
            # Extract job ID from URL
            parsed = urllib.parse.urlparse(href)
            params = urllib.parse.parse_qs(parsed.query)
            job_id = params.get("jk", [href])[0]

        if not job_id:
            job_id = card.get("data-jk", title[:50])

        # Company
        company_el = card.select_one("span.companyName, span[data-testid='company-name'], div.company")
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        # Location
        loc_el = card.select_one("div.companyLocation, div[data-testid='text-location'], span.location")
        location = loc_el.get_text(strip=True) if loc_el else ""

        # Salary
        sal_el = card.select_one("div.salary-snippet-container, div.metadata.salary-snippet-container, span.salary")
        salary_info = sal_el.get_text(strip=True) if sal_el else None

        # Snippet
        snippet_el = card.select_one("div.job-snippet, td.snip, div[class*='job-snippet']")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        is_remote = "remote" in (location + " " + title + " " + snippet).lower()

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
            description_snippet=snippet[:300],
            tags=[],
            preference_id=pref.id or 0,
        )
