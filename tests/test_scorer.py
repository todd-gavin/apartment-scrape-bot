"""Tests for the scoring system."""

from models import Listing
from scorer import compute_score, detect_amenities


def _make_listing(**kwargs) -> Listing:
    """Helper to create a listing with defaults."""
    defaults = {
        "source": "test",
        "source_url": "https://example.com/test",
        "price": 3000,
        "bedrooms": 1,
    }
    defaults.update(kwargs)
    return Listing(**defaults)


class TestComputeScore:
    def test_perfect_listing(self):
        """1BR at ideal price with all amenities = max score."""
        listing = _make_listing(
            price=2800,
            bedrooms=1,
            has_outdoor_space=True,
            has_garage=True,
            has_in_unit_laundry=True,
        )
        score = compute_score(listing)
        assert score == 100.0

    def test_bare_minimum(self):
        """Over-budget listing with no amenities."""
        listing = _make_listing(price=5000, bedrooms=3)
        score = compute_score(listing)
        assert score == 5.0  # Only 25% bedroom points

    def test_price_at_ideal(self):
        listing = _make_listing(price=3100)
        score = compute_score(listing)
        assert score == 55.0  # 35 price + 20 bedrooms

    def test_price_at_local_max(self):
        listing = _make_listing(price=3500)
        score = compute_score(listing)
        assert score == 40.0  # 20 price + 20 bedrooms

    def test_price_at_absolute_max(self):
        listing = _make_listing(price=4000)
        score = compute_score(listing)
        assert score == 25.0  # 5 price + 20 bedrooms

    def test_price_over_budget(self):
        listing = _make_listing(price=4500)
        score = compute_score(listing)
        assert score == 20.0  # 0 price + 20 bedrooms

    def test_two_bedroom(self):
        listing = _make_listing(price=3100, bedrooms=2)
        score = compute_score(listing)
        assert score == 45.0  # 35 price + 10 bedrooms

    def test_each_amenity_adds_15(self):
        base = _make_listing(price=3100, bedrooms=1)
        base_score = compute_score(base)

        for amenity in ["has_outdoor_space", "has_garage", "has_in_unit_laundry"]:
            listing = _make_listing(price=3100, bedrooms=1, **{amenity: True})
            assert compute_score(listing) == base_score + 15

    def test_zero_price_gets_no_price_points(self):
        listing = _make_listing(price=0)
        score = compute_score(listing)
        assert score == 20.0  # Only bedroom points

    def test_midrange_price(self):
        listing = _make_listing(price=3300)
        score = compute_score(listing)
        # 3300 is halfway between 3100-3500, so price = 35 - (0.5 * 15) = 27.5
        assert score == 47.5  # 27.5 price + 20 bedrooms


class TestDetectAmenities:
    def test_detects_balcony(self):
        result = detect_amenities("Spacious 1BR with private balcony")
        assert result["has_outdoor_space"] is True
        assert result["has_garage"] is False

    def test_detects_garage(self):
        result = detect_amenities("Includes 1-car garage and storage")
        assert result["has_garage"] is True

    def test_detects_in_unit_laundry(self):
        result = detect_amenities("Features in-unit laundry and modern kitchen")
        assert result["has_in_unit_laundry"] is True

    def test_detects_w_d_in_unit(self):
        result = detect_amenities("W/D in unit, hardwood floors")
        assert result["has_in_unit_laundry"] is True

    def test_no_amenities(self):
        result = detect_amenities("Nice apartment in great location")
        assert all(v is False for v in result.values())

    def test_all_amenities(self):
        text = "1BR with patio, private garage, and washer/dryer in unit"
        result = detect_amenities(text)
        assert all(v is True for v in result.values())

    def test_case_insensitive(self):
        result = detect_amenities("PRIVATE BALCONY with GARAGE")
        assert result["has_outdoor_space"] is True
        assert result["has_garage"] is True
