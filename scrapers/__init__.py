from .remoteok import RemoteOKScraper
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper
from .glassdoor import GlassdoorScraper

ALL_SCRAPERS = [
    RemoteOKScraper(),
    IndeedScraper(),
    LinkedInScraper(),
    GlassdoorScraper(),
]
