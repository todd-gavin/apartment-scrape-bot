"""WestsideRentals scraper — thin wrapper on Apartments.com (same parent company)."""

import logging

from scrapers.apartments_com import ApartmentsComScraper
from models import Listing
from config import WESTSIDERENTALS_SEARCH_URLS, PLAYWRIGHT_TIMEOUT

logger = logging.getLogger(__name__)


class WestsideRentalsScraper(ApartmentsComScraper):
    """WestsideRentals is owned by Apartments.com and shares the same listing data.

    This scraper reuses the Apartments.com parsing logic with WestsideRentals URLs.
    """

    name = "westsiderentals"

    async def scrape(self) -> list[Listing]:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth

        listings = []

        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.random_user_agent(),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            for search_url in WESTSIDERENTALS_SEARCH_URLS:
                try:
                    logger.info(f"[westsiderentals] Navigating to {search_url}")
                    await page.goto(search_url, timeout=PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")
                    await self.async_random_delay()

                    # WestsideRentals uses similar card structure
                    await page.wait_for_selector(
                        "article.placard, .listing-card, [class*='ListingCard']",
                        timeout=PLAYWRIGHT_TIMEOUT,
                    )

                    cards = await page.query_selector_all(
                        "article.placard, .listing-card, [class*='ListingCard']"
                    )
                    logger.info(f"[westsiderentals] Found {len(cards)} cards")

                    for card in cards:
                        try:
                            listing = await self._parse_card(card, page)
                            if listing:
                                listing.source = "westsiderentals"
                                listings.append(listing)
                        except Exception as e:
                            logger.warning(f"[westsiderentals] Error parsing card: {e}")

                except Exception as e:
                    logger.warning(f"[westsiderentals] Error on {search_url}: {e}")
                    self.errors.append(str(e))

                await self.async_random_delay()

            await browser.close()

        return listings
