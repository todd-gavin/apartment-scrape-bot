"""Abstract base class for all scrapers."""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod

from models import Listing
from config import REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, USER_AGENTS, MAX_RETRIES

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class that all site-specific scrapers inherit from."""

    name: str = "base"

    def __init__(self):
        self.results: list[Listing] = []
        self.errors: list[str] = []

    @abstractmethod
    async def scrape(self) -> list[Listing]:
        """Scrape the site and return a list of Listing objects."""
        ...

    async def run(self) -> list[Listing]:
        """Run the scraper with retry logic."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"[{self.name}] Scrape attempt {attempt}/{MAX_RETRIES}")
                self.results = await self.scrape()
                logger.info(f"[{self.name}] Found {len(self.results)} listings")
                return self.results
            except Exception as e:
                error_msg = f"[{self.name}] Attempt {attempt} failed: {e}"
                logger.warning(error_msg)
                self.errors.append(error_msg)
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt + random.random()
                    logger.info(f"[{self.name}] Retrying in {wait:.1f}s...")
                    await asyncio.sleep(wait)

        logger.error(f"[{self.name}] All {MAX_RETRIES} attempts failed")
        return []

    @staticmethod
    def random_delay():
        """Sleep for a random duration to avoid rate limiting."""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    @staticmethod
    async def async_random_delay():
        """Async sleep for a random duration."""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        await asyncio.sleep(delay)

    @staticmethod
    def random_user_agent() -> str:
        """Return a random user agent string."""
        return random.choice(USER_AGENTS)

    def get_status(self) -> dict:
        """Return scraper status for session logging."""
        return {
            "source": self.name,
            "status": "OK" if not self.errors else "FAILED",
            "found": len(self.results),
            "errors": len(self.errors),
            "error_messages": self.errors,
        }
