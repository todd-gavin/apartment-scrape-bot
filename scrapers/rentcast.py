"""RentCast API scraper — no browser needed, direct API calls."""

import logging

import httpx

from scrapers.base import BaseScraper
from models import Listing
from scorer import detect_amenities
from config import (
    RENTCAST_API_KEY,
    RENTCAST_BASE_URL,
    NEIGHBORHOODS,
    PRICE_ABSOLUTE_MAX,
    MIN_BEDROOMS,
    MAX_BEDROOMS,
)

logger = logging.getLogger(__name__)

# Approximate ZIP codes / cities for our target neighborhoods
SEARCH_LOCATIONS = [
    {"city": "Santa Monica", "state": "CA"},
    {"city": "Los Angeles", "state": "CA", "zipCode": "90049"},  # Brentwood
    {"city": "Los Angeles", "state": "CA", "zipCode": "90066"},  # Mar Vista
    {"city": "Los Angeles", "state": "CA", "zipCode": "90291"},  # Venice
    {"city": "Los Angeles", "state": "CA", "zipCode": "90405"},  # Ocean Park
]


class RentCastScraper(BaseScraper):
    name = "rentcast"

    async def scrape(self) -> list[Listing]:
        if not RENTCAST_API_KEY:
            logger.warning("[rentcast] RENTCAST_API_KEY not set — skipping")
            return []

        listings = []
        headers = {
            "Accept": "application/json",
            "X-Api-Key": RENTCAST_API_KEY,
        }

        async with httpx.AsyncClient(headers=headers, timeout=30) as client:
            for location in SEARCH_LOCATIONS:
                try:
                    params = {
                        "status": "Active",
                        "propertyType": "Apartment",
                        "bedrooms": MIN_BEDROOMS,
                        "maxRent": PRICE_ABSOLUTE_MAX,
                        "limit": 50,
                    }
                    params.update(location)

                    logger.info(f"[rentcast] Querying {location}")
                    response = await client.get(
                        f"{RENTCAST_BASE_URL}/listings/rental/long-term",
                        params=params,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        results = data if isinstance(data, list) else data.get("listings", data.get("results", []))
                        logger.info(f"[rentcast] Got {len(results)} results for {location}")

                        for item in results:
                            try:
                                listing = self._parse_result(item, location)
                                if listing:
                                    listings.append(listing)
                            except Exception as e:
                                logger.warning(f"[rentcast] Error parsing result: {e}")
                    elif response.status_code == 429:
                        logger.warning("[rentcast] Rate limited — stopping further requests")
                        break
                    else:
                        logger.warning(f"[rentcast] API returned {response.status_code}: {response.text[:200]}")
                        self.errors.append(f"API {response.status_code} for {location}")

                    await self.async_random_delay()

                except Exception as e:
                    logger.warning(f"[rentcast] Error querying {location}: {e}")
                    self.errors.append(str(e))

        return listings

    def _parse_result(self, item: dict, location: dict) -> Listing | None:
        """Parse a RentCast API result into a Listing."""
        price = item.get("price") or item.get("rent") or item.get("rentAmount", 0)
        if not price or price <= 0:
            return None

        address_parts = []
        if item.get("addressLine1"):
            address_parts.append(item["addressLine1"])
        if item.get("city"):
            address_parts.append(item["city"])
        if item.get("state"):
            address_parts.append(item["state"])
        address = ", ".join(address_parts)

        if not address:
            address = item.get("formattedAddress", "")

        # Build amenity text from features
        features = item.get("features", [])
        if isinstance(features, dict):
            features_text = " ".join(f"{k}: {v}" for k, v in features.items())
        elif isinstance(features, list):
            features_text = " ".join(str(f) for f in features)
        else:
            features_text = ""

        description = item.get("description", "")
        full_text = f"{description} {features_text} {address}"
        amenities = detect_amenities(full_text)

        # Determine neighborhood
        neighborhood = self._match_neighborhood(address, location)

        listing_url = item.get("listingUrl") or item.get("url", "")
        if not listing_url:
            # Construct a generic URL
            listing_id = item.get("id", item.get("listingId", ""))
            listing_url = f"https://www.rentcast.io/listing/{listing_id}" if listing_id else ""

        return Listing(
            source="rentcast",
            source_url=listing_url,
            source_listing_id=str(item.get("id", item.get("listingId", ""))),
            title=item.get("title", address),
            address=address,
            neighborhood=neighborhood,
            price=int(price),
            bedrooms=item.get("bedrooms", MIN_BEDROOMS),
            bathrooms=item.get("bathrooms"),
            sqft=item.get("squareFootage") or item.get("sqft"),
            property_type=item.get("propertyType", ""),
            has_outdoor_space=amenities["has_outdoor_space"],
            has_garage=amenities["has_garage"],
            has_in_unit_laundry=amenities["has_in_unit_laundry"],
            raw_amenities=features_text[:500],
        )

    @staticmethod
    def _match_neighborhood(address: str, location: dict) -> str:
        """Match address to a neighborhood name."""
        addr_lower = address.lower()
        for n in NEIGHBORHOODS:
            if n.lower() in addr_lower:
                return n

        # Fallback based on ZIP code
        zip_map = {
            "90049": "Brentwood",
            "90066": "Mar Vista",
            "90291": "Venice",
            "90405": "Ocean Park",
            "90401": "Santa Monica",
            "90402": "Santa Monica",
            "90403": "Santa Monica",
            "90404": "Santa Monica",
        }
        zip_code = location.get("zipCode", "")
        return zip_map.get(zip_code, location.get("city", ""))
