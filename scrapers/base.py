import logging
import re
from abc import ABC, abstractmethod

from ..models import Job, Preferences

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    name: str = "base"

    @abstractmethod
    def search(self, preferences: Preferences) -> list[Job]:
        ...

    def _matches_salary(self, salary_text: str | None, pref: Preferences) -> bool:
        if not salary_text or (pref.salary_min is None and pref.salary_max is None):
            return True
        numbers = re.findall(r"[\d,]+", salary_text.replace(",", ""))
        if not numbers:
            return True
        amounts = []
        for n in numbers:
            try:
                val = int(n)
                if val > 1000:  # filter out non-salary numbers
                    amounts.append(val)
            except ValueError:
                continue
        if not amounts:
            return True
        max_salary = max(amounts)
        if pref.salary_min and max_salary < pref.salary_min:
            return False
        if pref.salary_max:
            min_salary = min(amounts)
            if min_salary > pref.salary_max:
                return False
        return True

    def _matches_experience(self, text: str, level: str) -> bool:
        if level == "any":
            return True
        text_lower = text.lower()
        level_keywords = {
            "entry": ["entry", "junior", "jr", "graduate", "intern", "0-2 years", "1-2 years"],
            "mid": ["mid", "intermediate", "2-5 years", "3-5 years", "2+ years", "3+ years"],
            "senior": ["senior", "sr", "lead", "principal", "staff", "5+ years", "7+ years", "10+ years"],
        }
        keywords = level_keywords.get(level, [])
        return any(kw in text_lower for kw in keywords) if keywords else True

    def _skill_match_score(self, text: str, skills: list[str]) -> float:
        if not skills:
            return 1.0
        text_lower = text.lower()
        matched = sum(1 for s in skills if s.lower() in text_lower)
        return matched / len(skills)
