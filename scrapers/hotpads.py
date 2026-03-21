"""HotPads scraper — Playwright (JS-rendered, Zillow Group)."""

import logging
import re

from scrapers.base import BaseScraper
from models import Listing
from scorer import detect_amenities
from config import HOTPADS_SEARCH_URLS, PLAYWRIGHT_TIMEOUT

logger = logging.getLogger(__name__)


class HotPadsScraper(BaseScraper):
    name = "hotpads"

    async def scrape(self) -> list[Listing]:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth

        listings = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.random_user_agent(),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            await Stealth().use_async(page)

            for search_url in HOTPADS_SEARCH_URLS:
                try:
                    logger.info(f"[hotpads] Navigating to {search_url}")
                    await page.goto(search_url, timeout=PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")
                    await self.async_random_delay()

                    # Wait for listings
                    await page.wait_for_selector("[class*='ListingCard'], .listing-card", timeout=PLAYWRIGHT_TIMEOUT)

                    # Scroll to load more
                    for _ in range(3):
                        await page.evaluate("window.scrollBy(0, window.innerHeight)")
                        await page.wait_for_timeout(1500)

                    cards = await page.query_selector_all("[class*='ListingCard'], .listing-card, [data-testid*='listing']")
                    logger.info(f"[hotpads] Found {len(cards)} cards")

                    for card in cards:
                        try:
                            listing = await self._parse_card(card)
                            if listing:
                                listings.append(listing)
                        except Exception as e:
                            logger.warning(f"[hotpads] Error parsing card: {e}")

                except Exception as e:
                    logger.warning(f"[hotpads] Error on {search_url}: {e}")
                    self.errors.append(str(e))

                await self.async_random_delay()

            await browser.close()

        return listings

    async def _parse_card(self, card) -> Listing | None:
        """Parse a HotPads listing card."""
        # Get link
        link = await card.query_selector("a")
        if not link:
            return None
        url = await link.get_attribute("href") or ""
        if not url.startswith("http"):
            url = f"https://hotpads.com{url}"

        text = await card.inner_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Price
        price = 0
        for line in lines:
            match = re.search(r"\$?([\d,]+)", line)
            if match:
                p = int(match.group(1).replace(",", ""))
                if 500 <= p <= 10000:
                    price = p
                    break

        # Bedrooms
        bedrooms = 1
        for line in lines:
            match = re.search(r"(\d+)\s*(?:bd|bed|br)", line, re.IGNORECASE)
            if match:
                bedrooms = int(match.group(1))
                break

        # Address
        address = lines[0] if lines else ""
        if re.match(r"^\$", address) and len(lines) > 1:
            address = lines[1]

        amenities = detect_amenities(text)

        return Listing(
            source="hotpads",
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
