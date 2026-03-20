"""Zumper scraper — Playwright (JS-rendered SPA)."""

import logging
import re

from scrapers.base import BaseScraper
from models import Listing
from scorer import detect_amenities
from config import ZUMPER_SEARCH_URLS, PLAYWRIGHT_TIMEOUT

logger = logging.getLogger(__name__)


class ZumperScraper(BaseScraper):
    name = "zumper"

    async def scrape(self) -> list[Listing]:
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth_async

        listings = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.random_user_agent(),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            await stealth_async(page)

            for search_url in ZUMPER_SEARCH_URLS:
                try:
                    logger.info(f"[zumper] Navigating to {search_url}")
                    await page.goto(search_url, timeout=PLAYWRIGHT_TIMEOUT, wait_until="networkidle")
                    await self.async_random_delay()

                    # Scroll to load more listings
                    for _ in range(3):
                        await page.evaluate("window.scrollBy(0, window.innerHeight)")
                        await page.wait_for_timeout(1500)

                    # Extract listing cards
                    cards = await page.query_selector_all("[class*='ListingCard'], [data-testid='listing-card']")
                    if not cards:
                        cards = await page.query_selector_all("a[href*='/apartments-for-rent/'], a[href*='/apartment/']")

                    logger.info(f"[zumper] Found {len(cards)} cards")

                    for card in cards:
                        try:
                            listing = await self._parse_card(card)
                            if listing:
                                listings.append(listing)
                        except Exception as e:
                            logger.warning(f"[zumper] Error parsing card: {e}")

                except Exception as e:
                    logger.warning(f"[zumper] Error on {search_url}: {e}")
                    self.errors.append(str(e))

                await self.async_random_delay()

            await browser.close()

        return listings

    async def _parse_card(self, card) -> Listing | None:
        """Parse a Zumper listing card."""
        # Get URL
        url = await card.get_attribute("href")
        if not url:
            link = await card.query_selector("a")
            if link:
                url = await link.get_attribute("href")
        if not url:
            return None
        if not url.startswith("http"):
            url = f"https://www.zumper.com{url}"

        # Get all text content for parsing
        text = await card.inner_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Extract price
        price = 0
        for line in lines:
            price_match = re.search(r"\$?([\d,]+)(?:\s*/\s*mo)?", line)
            if price_match:
                p = int(price_match.group(1).replace(",", ""))
                if 500 <= p <= 10000:  # Reasonable rent range
                    price = p
                    break

        # Extract bedrooms
        bedrooms = 1
        for line in lines:
            bed_match = re.search(r"(\d+)\s*(?:bd|bed|br|bedroom)", line, re.IGNORECASE)
            if bed_match:
                bedrooms = int(bed_match.group(1))
                break
            if "studio" in line.lower():
                bedrooms = 0
                break

        # Extract address (usually one of the first lines)
        address = lines[0] if lines else ""
        # If first line looks like a price, use next line
        if re.match(r"^\$", address) and len(lines) > 1:
            address = lines[1]

        amenities = detect_amenities(text)

        return Listing(
            source="zumper",
            source_url=url,
            title=address,
            address=address,
            neighborhood=self._extract_neighborhood(text),
            price=price,
            bedrooms=bedrooms,
            has_outdoor_space=amenities["has_outdoor_space"],
            has_garage=amenities["has_garage"],
            has_in_unit_laundry=amenities["has_in_unit_laundry"],
            raw_amenities=text[:500],
        )

    @staticmethod
    def _extract_neighborhood(text: str) -> str:
        from config import NEIGHBORHOODS
        text_lower = text.lower()
        for n in NEIGHBORHOODS:
            if n.lower() in text_lower:
                return n
        return ""
