"""Tests for the database persistence layer."""

import os
import tempfile

from models import Listing
from database import init_db, upsert_listing, get_new_listings, mark_notified, get_all_active_ranked, get_stats


def _make_listing(**kwargs) -> Listing:
    defaults = {
        "source": "test",
        "source_url": "https://example.com/listing1",
        "title": "Test Listing",
        "address": "123 Main St",
        "neighborhood": "Santa Monica",
        "price": 3000,
        "bedrooms": 1,
    }
    defaults.update(kwargs)
    return Listing(**defaults)


class TestDatabase:
    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.db_path)

    def teardown_method(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_insert_new_listing(self):
        listing = _make_listing()
        is_new = upsert_listing(listing, self.db_path)
        assert is_new is True

    def test_upsert_existing_listing(self):
        listing = _make_listing()
        upsert_listing(listing, self.db_path)
        is_new = upsert_listing(listing, self.db_path)
        assert is_new is False

    def test_get_new_listings(self):
        listing = _make_listing(score=75.0)
        upsert_listing(listing, self.db_path)
        new = get_new_listings(self.db_path)
        assert len(new) == 1
        assert new[0].price == 3000

    def test_mark_notified(self):
        listing = _make_listing()
        upsert_listing(listing, self.db_path)
        new = get_new_listings(self.db_path)
        assert len(new) == 1

        mark_notified([new[0].listing_id], self.db_path)
        new_after = get_new_listings(self.db_path)
        assert len(new_after) == 0

    def test_get_all_active_ranked(self):
        l1 = _make_listing(source_url="https://example.com/1", price=2800)
        l1.score = 85.0
        l2 = _make_listing(source_url="https://example.com/2", price=3500)
        l2.score = 45.0

        upsert_listing(l1, self.db_path)
        upsert_listing(l2, self.db_path)

        ranked = get_all_active_ranked(self.db_path)
        assert len(ranked) == 2
        assert ranked[0].score >= ranked[1].score

    def test_get_stats(self):
        l1 = _make_listing(source="craigslist", source_url="https://example.com/1")
        l2 = _make_listing(source="zillow", source_url="https://example.com/2")
        upsert_listing(l1, self.db_path)
        upsert_listing(l2, self.db_path)

        stats = get_stats(self.db_path)
        assert stats["total_active"] == 2
        assert "craigslist" in stats["by_source"]
        assert "zillow" in stats["by_source"]

    def test_different_urls_are_different_listings(self):
        l1 = _make_listing(source_url="https://example.com/a")
        l2 = _make_listing(source_url="https://example.com/b")
        assert upsert_listing(l1, self.db_path) is True
        assert upsert_listing(l2, self.db_path) is True
        assert get_stats(self.db_path)["total_active"] == 2
