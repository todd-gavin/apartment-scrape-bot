"""Tests for the email notifier (mocked)."""

from unittest.mock import patch, MagicMock

from models import Listing
from notifier import _build_html


def _make_listing(**kwargs) -> Listing:
    defaults = {
        "source": "test",
        "source_url": "https://example.com/test",
        "title": "Test Apt",
        "neighborhood": "Santa Monica",
        "price": 3000,
        "bedrooms": 1,
        "score": 70.0,
    }
    defaults.update(kwargs)
    return Listing(**defaults)


class TestBuildHtml:
    def test_contains_listing_data(self):
        listings = [
            _make_listing(price=2800, score=85.0, neighborhood="Venice"),
            _make_listing(price=3500, score=45.0, source_url="https://example.com/2"),
        ]
        stats = {"total_active": 10}
        html = _build_html(listings, stats)

        assert "$2,800" in html
        assert "$3,500" in html
        assert "Venice" in html
        assert "85.0" in html
        assert "10 total active" in html

    def test_sorts_by_score_descending(self):
        listings = [
            _make_listing(score=40.0, source_url="https://example.com/low"),
            _make_listing(score=90.0, source_url="https://example.com/high"),
        ]
        html = _build_html(listings, {"total_active": 2})
        # The 90.0 score should appear before 40.0
        pos_high = html.index("90.0")
        pos_low = html.index("40.0")
        assert pos_high < pos_low

    def test_amenity_summary_in_html(self):
        listing = _make_listing(
            has_outdoor_space=True,
            has_garage=True,
            has_in_unit_laundry=True,
        )
        html = _build_html([listing], {"total_active": 1})
        assert "Outdoor" in html
        assert "Garage" in html
        assert "In-Unit W/D" in html

    def test_single_listing_subject_grammar(self):
        html = _build_html(
            [_make_listing()],
            {"total_active": 1},
        )
        assert "1 new listing found" in html.lower()
