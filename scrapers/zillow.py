"""Zillow scraper — Camoufox (stealth Firefox to bypass HUMAN Security)."""

import json
import logging
import re

from scrapers.base import BaseScraper
from models import Listing
from scorer import detect_amenities
from config import ZILLOW_SEARCH_URLS, PLAYWRIGHT_TIMEOUT

logger = logging.getLogger(__name__)


class ZillowScraper(BaseScraper):
    name = "zillow"

    async def scrape(self) -> list[Listing]:
        from camoufox.async_api import AsyncCamoufox

        listings = []

        async with AsyncCamoufox(headless=True) as browser:
            page = await browser.new_page()

            for search_url in ZILLOW_SEARCH_URLS:
                try:
                    logger.info(f"[zillow] Navigating to {search_url}")
                    await page.goto(search_url, timeout=PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")
                    await self.async_random_delay()

                    # Wait for page to fully render
                    await page.wait_for_timeout(3000)

                    # Try to extract __NEXT_DATA__ JSON
                    page_content = await page.content()
                    extracted = self._extract_next_data(page_content)

                    if extracted:
                        listings.extend(extracted)
                        logger.info(f"[zillow] Extracted {len(extracted)} listings from __NEXT_DATA__")
                    else:
                        # Log page title to help debug bot detection
                        title = await page.title()
                        logger.info(f"[zillow] Page title: {title}")
                        # Fallback: parse DOM
                        dom_listings = await self._parse_dom(page)
                        listings.extend(dom_listings)
                        logger.info(f"[zillow] Extracted {len(dom_listings)} listings from DOM")

                except Exception as e:
                    logger.warning(f"[zillow] Error on {search_url}: {e}")
                    self.errors.append(str(e))

                await self.async_random_delay()

        return listings

    def _extract_next_data(self, html: str) -> list[Listing]:
        """Extract listing data from Zillow's __NEXT_DATA__ script tag."""
        listings = []

        # Find the __NEXT_DATA__ script
        match = re.search(
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not match:
            return []

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("[zillow] Failed to parse __NEXT_DATA__ JSON")
            return []

        # Navigate the JSON structure to find listings
        try:
            search_results = (
                data.get("props", {})
                .get("pageProps", {})
                .get("searchPageState", {})
                .get("cat1", {})
                .get("searchResults", {})
                .get("listResults", [])
            )
        except (AttributeError, TypeError):
            logger.warning("[zillow] Unexpected __NEXT_DATA__ structure")
            return []

        for result in search_results:
            try:
                listing = self._parse_json_result(result)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"[zillow] Error parsing JSON result: {e}")

        return listings

    def _parse_json_result(self, result: dict) -> Listing | None:
        """Parse a single listing from Zillow's JSON data."""
        detail_url = result.get("detailUrl", "")
        if not detail_url:
            return None
        if not detail_url.startswith("http"):
            detail_url = f"https://www.zillow.com{detail_url}"

        price = result.get("unformattedPrice", 0) or result.get("price", 0)
        if isinstance(price, str):
            price_match = re.search(r"[\d,]+", price)
            price = int(price_match.group().replace(",", "")) if price_match else 0

        address_info = result.get("address", "")
        if isinstance(address_info, dict):
            address = f"{address_info.get('streetAddress', '')}, {address_info.get('city', '')}"
        else:
            address = str(address_info)

        bedrooms = result.get("beds", 1) or 1
        bathrooms = result.get("baths", None)
        sqft = result.get("area", None)

        # Build text for amenity detection
        listing_text = result.get("statusText", "")
        amenities = detect_amenities(f"{listing_text} {address}")

        listing = Listing(
            source="zillow",
            source_url=detail_url,
            source_listing_id=str(result.get("zpid", "")),
            title=result.get("statusText", address),
            address=address,
            neighborhood=self._extract_neighborhood(address),
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft=sqft,
            has_outdoor_space=amenities["has_outdoor_space"],
            has_garage=amenities["has_garage"],
            has_in_unit_laundry=amenities["has_in_unit_laundry"],
        )
        return listing

    async def _parse_dom(self, page) -> list[Listing]:
        """Fallback: parse listings from the DOM."""
        listings = []

        cards = await page.query_selector_all("article[data-test='property-card'], .list-card")
        for card in cards:
            try:
                # Get link
                link = await card.query_selector("a[data-test='property-card-link'], a.list-card-link")
                if not link:
                    continue
                url = await link.get_attribute("href") or ""
                if not url.startswith("http"):
                    url = f"https://www.zillow.com{url}"

                # Get price
                price_el = await card.query_selector("[data-test='property-card-price'], .list-card-price")
                price_text = await price_el.inner_text() if price_el else ""
                price = self._extract_price(price_text)

                # Get address
                addr_el = await card.query_selector("address, [data-test='property-card-addr']")
                address = await addr_el.inner_text() if addr_el else ""

                # Get details
                details_el = await card.query_selector("[data-test='property-card-details'], .list-card-details")
                details = await details_el.inner_text() if details_el else ""
                bedrooms = self._extract_bedrooms(details)

                amenities = detect_amenities(f"{details} {address}")

                listing = Listing(
                    source="zillow",
                    source_url=url,
                    title=address,
                    address=address.strip(),
                    neighborhood=self._extract_neighborhood(address),
                    price=price,
                    bedrooms=bedrooms,
                    has_outdoor_space=amenities["has_outdoor_space"],
                    has_garage=amenities["has_garage"],
                    has_in_unit_laundry=amenities["has_in_unit_laundry"],
                    raw_amenities=details,
                )
                listings.append(listing)
            except Exception as e:
                logger.warning(f"[zillow] Error parsing DOM card: {e}")

        return listings

    @staticmethod
    def _extract_price(text: str) -> int:
        prices = re.findall(r"\$?([\d,]+)", text)
        if prices:
            return min(int(p.replace(",", "")) for p in prices)
        return 0

    @staticmethod
    def _extract_bedrooms(text: str) -> int:
        match = re.search(r"(\d+)\s*(?:bd|bed|br)", text, re.IGNORECASE)
        return int(match.group(1)) if match else 1

    @staticmethod
    def _extract_neighborhood(address: str) -> str:
        from config import NEIGHBORHOODS
        addr_lower = address.lower()
        for n in NEIGHBORHOODS:
            if n.lower() in addr_lower:
                return n
        return ""
