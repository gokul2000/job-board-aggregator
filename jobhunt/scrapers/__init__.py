from .remoteok import RemoteOKScraper
from .linkedin import LinkedInScraper
from .themuse import TheMuseScraper
from .adzuna import AdzunaScraper
from .arbeitnow import ArbeitnowScraper

ALL_SCRAPERS = [
    RemoteOKScraper(),      # Free, no auth - remote jobs
    LinkedInScraper(),      # HTML scraping - general jobs
    TheMuseScraper(),       # Free API, no auth - general jobs
    AdzunaScraper(),        # Free API, requires key - great salary data
    ArbeitnowScraper(),     # Free API, no auth - tech/remote jobs
]
