"""Craigslist scraper — httpx + BeautifulSoup (server-rendered HTML)."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models import Listing
from scorer import detect_amenities
from config import (
    CRAIGSLIST_BASE_URL,
    CRAIGSLIST_PARAMS,
    NEIGHBORHOODS,
)

logger = logging.getLogger(__name__)


class CraigslistScraper(BaseScraper):
    name = "craigslist"

    async def scrape(self) -> list[Listing]:
        listings = []
        headers = {"User-Agent": self.random_user_agent()}

        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
            # Fetch the search results page
            response = await client.get(CRAIGSLIST_BASE_URL, params=CRAIGSLIST_PARAMS)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Craigslist uses <li class="cl-static-search-result"> for listings
            result_items = soup.select("li.cl-static-search-result")
            if not result_items:
                # Fallback: try older Craigslist format
                result_items = soup.select(".result-row")

            logger.info(f"[craigslist] Found {len(result_items)} result items on search page")

            for item in result_items:
                try:
                    listing = self._parse_search_result(item)
                    if listing and self._matches_neighborhood(listing):
                        listings.append(listing)
                except Exception as e:
                    logger.warning(f"[craigslist] Error parsing result: {e}")
                    continue

            logger.info(f"[craigslist] {len(listings)} listings match target neighborhoods")

            # Follow detail links to get amenity info (limit to avoid long runs)
            max_details = 50
            for i, listing in enumerate(listings[:max_details]):
                try:
                    await self.async_random_delay()
                    detail_response = await client.get(listing.source_url)
                    if detail_response.status_code == 200:
                        self._enrich_from_detail(listing, detail_response.text)
                except Exception as e:
                    logger.warning(f"[craigslist] Error fetching detail for {listing.source_url}: {e}")

            if len(listings) > max_details:
                logger.info(f"[craigslist] Skipped details for {len(listings) - max_details} listings (limit {max_details})")

        return listings

    def _parse_search_result(self, item) -> Listing | None:
        """Parse a single search result item into a Listing."""
        # Try to get the link
        link_tag = item.select_one("a")
        if not link_tag:
            return None

        url = link_tag.get("href", "")
        if not url:
            return None

        # Get title
        title_tag = item.select_one(".title, .result-title, a")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Get price
        price_tag = item.select_one(".price, .result-price")
        price = 0
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            price_match = re.search(r"\$?([\d,]+)", price_text)
            if price_match:
                price = int(price_match.group(1).replace(",", ""))

        # Get neighborhood/location
        hood_tag = item.select_one(".neighborhood, .result-hood, .meta .location")
        neighborhood = ""
        if hood_tag:
            neighborhood = hood_tag.get_text(strip=True).strip("() ")

        # Extract post ID from URL
        source_id = ""
        id_match = re.search(r"/(\d+)\.html", url)
        if id_match:
            source_id = id_match.group(1)

        return Listing(
            source="craigslist",
            source_url=url,
            source_listing_id=source_id,
            title=title,
            address="",  # Craigslist doesn't always show address in search
            neighborhood=self._normalize_neighborhood(neighborhood),
            price=price,
            bedrooms=1,  # We're filtering for 1BR in search params
        )

    def _enrich_from_detail(self, listing: Listing, html: str) -> None:
        """Parse detail page to extract amenities and additional info."""
        soup = BeautifulSoup(html, "lxml")

        # Get the full description text
        body = soup.select_one("#postingbody")
        body_text = body.get_text(" ", strip=True) if body else ""

        # Get attribute group text (often has structured amenities)
        attrs = soup.select(".attrgroup span")
        attr_text = " ".join(a.get_text(strip=True) for a in attrs)

        # Combine all text for amenity detection
        full_text = f"{listing.title} {body_text} {attr_text}"
        listing.raw_amenities = attr_text

        amenities = detect_amenities(full_text)
        listing.has_outdoor_space = amenities["has_outdoor_space"]
        listing.has_garage = amenities["has_garage"]
        listing.has_in_unit_laundry = amenities["has_in_unit_laundry"]

        # Try to extract bedrooms/bathrooms from attributes
        for attr in attrs:
            text = attr.get_text(strip=True).lower()
            br_match = re.search(r"(\d+)br", text)
            if br_match:
                listing.bedrooms = int(br_match.group(1))
            ba_match = re.search(r"([\d.]+)ba", text)
            if ba_match:
                listing.bathrooms = float(ba_match.group(1))
            sqft_match = re.search(r"(\d+)\s*ft", text)
            if sqft_match:
                listing.sqft = int(sqft_match.group(1))

        # Try to get address from map section
        map_addr = soup.select_one(".mapaddress")
        if map_addr:
            listing.address = map_addr.get_text(strip=True)

    def _matches_neighborhood(self, listing: Listing) -> bool:
        """Check if the listing is in one of our target neighborhoods."""
        if not listing.neighborhood:
            # Also check the title for neighborhood clues
            return any(
                n.lower() in listing.title.lower()
                for n in NEIGHBORHOODS
            )
        return any(
            n.lower() in listing.neighborhood.lower()
            for n in NEIGHBORHOODS
        )

    @staticmethod
    def _normalize_neighborhood(raw: str) -> str:
        """Normalize neighborhood names to our standard list."""
        raw_lower = raw.lower()
        for n in NEIGHBORHOODS:
            if n.lower() in raw_lower:
                return n
        return raw
