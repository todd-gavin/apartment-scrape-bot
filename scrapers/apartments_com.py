"""Apartments.com scraper — Playwright (JS-rendered, Akamai WAF)."""

import logging
import re

from scrapers.base import BaseScraper
from models import Listing
from scorer import detect_amenities
from config import APARTMENTS_COM_SEARCH_URLS, PLAYWRIGHT_TIMEOUT

logger = logging.getLogger(__name__)


class ApartmentsComScraper(BaseScraper):
    name = "apartments.com"

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

            for search_url in APARTMENTS_COM_SEARCH_URLS:
                try:
                    logger.info(f"[apartments.com] Navigating to {search_url}")
                    await page.goto(search_url, timeout=PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")
                    await self.async_random_delay()

                    # Wait for listing cards to appear
                    await page.wait_for_selector("article.placard, li.mortar-wrapper", timeout=PLAYWRIGHT_TIMEOUT)

                    # Extract listing cards
                    cards = await page.query_selector_all("article.placard, li.mortar-wrapper")
                    logger.info(f"[apartments.com] Found {len(cards)} cards on page")

                    for card in cards:
                        try:
                            listing = await self._parse_card(card, page)
                            if listing:
                                listings.append(listing)
                        except Exception as e:
                            logger.warning(f"[apartments.com] Error parsing card: {e}")

                except Exception as e:
                    logger.warning(f"[apartments.com] Error on {search_url}: {e}")
                    self.errors.append(str(e))

                await self.async_random_delay()

            await browser.close()

        return listings

    async def _parse_card(self, card, page) -> Listing | None:
        """Parse a single listing card element."""
        # Get the detail link
        link = await card.query_selector("a.property-link, a[data-tid='property-title']")
        if not link:
            link = await card.query_selector("a")
        if not link:
            return None

        url = await link.get_attribute("href") or ""
        if not url.startswith("http"):
            url = f"https://www.apartments.com{url}"

        # Get title
        title_el = await card.query_selector(".property-title, [data-tid='property-title']")
        title = await title_el.inner_text() if title_el else ""

        # Get price
        price_el = await card.query_selector(".property-pricing, .price-range, [data-tid='property-pricing']")
        price_text = await price_el.inner_text() if price_el else ""
        price = self._extract_price(price_text)

        # Get address
        addr_el = await card.query_selector(".property-address, [data-tid='property-address']")
        address = await addr_el.inner_text() if addr_el else ""

        # Get beds
        beds_el = await card.query_selector(".property-beds, [data-tid='property-beds']")
        beds_text = await beds_el.inner_text() if beds_el else ""
        bedrooms = self._extract_bedrooms(beds_text)

        # Get amenities text
        amenity_el = await card.query_selector(".property-amenities")
        amenity_text = await amenity_el.inner_text() if amenity_el else ""

        full_text = f"{title} {amenity_text} {address}"
        amenities = detect_amenities(full_text)

        listing = Listing(
            source="apartments.com",
            source_url=url,
            title=title.strip(),
            address=address.strip(),
            neighborhood=self._extract_neighborhood(address),
            price=price,
            bedrooms=bedrooms,
            has_outdoor_space=amenities["has_outdoor_space"],
            has_garage=amenities["has_garage"],
            has_in_unit_laundry=amenities["has_in_unit_laundry"],
            raw_amenities=amenity_text.strip(),
        )
        return listing

    @staticmethod
    def _extract_price(text: str) -> int:
        """Extract the lowest price from a price string."""
        prices = re.findall(r"\$?([\d,]+)", text)
        if prices:
            return min(int(p.replace(",", "")) for p in prices)
        return 0

    @staticmethod
    def _extract_bedrooms(text: str) -> int:
        match = re.search(r"(\d+)\s*(?:bed|br|bedroom)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        if "studio" in text.lower():
            return 0
        return 1  # Default for our filtered search

    @staticmethod
    def _extract_neighborhood(address: str) -> str:
        from config import NEIGHBORHOODS
        addr_lower = address.lower()
        for n in NEIGHBORHOODS:
            if n.lower() in addr_lower:
                return n
        return ""
