"""Preferability scoring for rental listings."""

from models import Listing
from config import PRICE_IDEAL, PRICE_LOCAL_MAX, PRICE_ABSOLUTE_MAX, SCORE_WEIGHTS


def compute_score(listing: Listing) -> float:
    """Compute a 0-100 preferability score for a listing.

    Components:
      - Price (35 pts): closer to ideal budget = higher score
      - Bedrooms (20 pts): 1BR preferred
      - Outdoor space (15 pts): deck/patio/balcony/yard
      - Garage (15 pts): enclosed 1-car garage
      - In-unit laundry (15 pts): washer/dryer in unit
    """
    score = 0.0

    # Price (max 35 points)
    w = SCORE_WEIGHTS["price"]
    if listing.price <= 0:
        score += 0
    elif listing.price <= PRICE_IDEAL:
        score += w
    elif listing.price <= PRICE_LOCAL_MAX:
        # Linear decay: 35 -> 20 as price goes 3100 -> 3500
        ratio = (listing.price - PRICE_IDEAL) / (PRICE_LOCAL_MAX - PRICE_IDEAL)
        score += w - (ratio * 15)
    elif listing.price <= PRICE_ABSOLUTE_MAX:
        # Linear decay: 20 -> 5 as price goes 3500 -> 4000
        ratio = (listing.price - PRICE_LOCAL_MAX) / (PRICE_ABSOLUTE_MAX - PRICE_LOCAL_MAX)
        score += 20 - (ratio * 15)
    # Over budget = 0 price points

    # Bedrooms (max 20 points)
    w = SCORE_WEIGHTS["bedrooms"]
    if listing.bedrooms == 1:
        score += w
    elif listing.bedrooms == 2:
        score += w * 0.5
    elif listing.bedrooms > 0:
        score += w * 0.25

    # Outdoor space (max 15 points)
    if listing.has_outdoor_space:
        score += SCORE_WEIGHTS["outdoor_space"]

    # Garage (max 15 points)
    if listing.has_garage:
        score += SCORE_WEIGHTS["garage"]

    # In-unit laundry (max 15 points)
    if listing.has_in_unit_laundry:
        score += SCORE_WEIGHTS["in_unit_laundry"]

    return round(score, 1)


def detect_amenities(text: str) -> dict[str, bool]:
    """Detect amenities from a text description.

    Returns dict with keys: has_outdoor_space, has_garage, has_in_unit_laundry.
    """
    from config import OUTDOOR_KEYWORDS, GARAGE_KEYWORDS, LAUNDRY_KEYWORDS

    text_lower = text.lower()

    return {
        "has_outdoor_space": any(kw in text_lower for kw in OUTDOOR_KEYWORDS),
        "has_garage": any(kw in text_lower for kw in GARAGE_KEYWORDS),
        "has_in_unit_laundry": any(kw in text_lower for kw in LAUNDRY_KEYWORDS),
    }
