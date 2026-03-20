"""Data model for rental listings."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib


@dataclass
class Listing:
    """A single rental listing scraped from a housing site."""

    # Identity
    source: str  # "craigslist", "apartments.com", etc.
    source_url: str
    source_listing_id: str = ""

    # Core details
    title: str = ""
    address: str = ""
    neighborhood: str = ""
    price: int = 0
    bedrooms: int = 0
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None
    property_type: str = ""  # "apartment", "house", "condo", etc.

    # Preference features
    has_outdoor_space: bool = False
    has_garage: bool = False
    has_in_unit_laundry: bool = False

    # Scoring (computed)
    score: float = 0.0

    # Metadata
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    notified: bool = False
    raw_amenities: str = ""

    @property
    def listing_id(self) -> str:
        """Generate a unique ID from source + URL."""
        raw = f"{self.source}:{self.source_url}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def amenity_summary(self) -> str:
        """Human-readable summary of matched amenities."""
        amenities = []
        if self.has_outdoor_space:
            amenities.append("Outdoor")
        if self.has_garage:
            amenities.append("Garage")
        if self.has_in_unit_laundry:
            amenities.append("In-Unit W/D")
        return ", ".join(amenities) if amenities else "None"

    def price_tier(self) -> str:
        """Categorize price into budget tiers."""
        if self.price <= 3100:
            return "Ideal"
        elif self.price <= 3500:
            return "Local Max"
        elif self.price <= 4000:
            return "Absolute Max"
        else:
            return "Over Budget"
