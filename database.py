"""SQLite persistence layer for rental listings."""

import sqlite3
from datetime import datetime
from typing import Optional

from models import Listing
from config import DB_PATH


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Get a database connection with WAL mode enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create tables and indexes if they don't exist."""
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS listings (
            listing_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_listing_id TEXT DEFAULT '',
            title TEXT DEFAULT '',
            address TEXT DEFAULT '',
            neighborhood TEXT DEFAULT '',
            price INTEGER DEFAULT 0,
            bedrooms INTEGER DEFAULT 0,
            bathrooms REAL,
            sqft INTEGER,
            property_type TEXT DEFAULT '',
            has_outdoor_space INTEGER DEFAULT 0,
            has_garage INTEGER DEFAULT 0,
            has_in_unit_laundry INTEGER DEFAULT 0,
            score REAL DEFAULT 0,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            notified INTEGER DEFAULT 0,
            raw_amenities TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_source ON listings(source);
        CREATE INDEX IF NOT EXISTS idx_neighborhood ON listings(neighborhood);
        CREATE INDEX IF NOT EXISTS idx_score ON listings(score DESC);
        CREATE INDEX IF NOT EXISTS idx_notified ON listings(notified);
        CREATE INDEX IF NOT EXISTS idx_active ON listings(is_active);
    """)
    conn.commit()
    conn.close()


def upsert_listing(listing: Listing, db_path: str = DB_PATH) -> bool:
    """Insert a new listing or update last_seen for existing.

    Returns True if this is a new listing, False if updated.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    existing = cursor.execute(
        "SELECT listing_id FROM listings WHERE listing_id = ?",
        (listing.listing_id,),
    ).fetchone()

    now = datetime.now().isoformat()

    if existing:
        cursor.execute(
            """UPDATE listings
               SET last_seen = ?, is_active = 1, price = ?, score = ?
               WHERE listing_id = ?""",
            (now, listing.price, listing.score, listing.listing_id),
        )
        conn.commit()
        conn.close()
        return False
    else:
        cursor.execute(
            """INSERT INTO listings (
                listing_id, source, source_url, source_listing_id,
                title, address, neighborhood, price,
                bedrooms, bathrooms, sqft, property_type,
                has_outdoor_space, has_garage, has_in_unit_laundry,
                score, first_seen, last_seen, is_active, notified, raw_amenities
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                listing.listing_id,
                listing.source,
                listing.source_url,
                listing.source_listing_id,
                listing.title,
                listing.address,
                listing.neighborhood,
                listing.price,
                listing.bedrooms,
                listing.bathrooms,
                listing.sqft,
                listing.property_type,
                int(listing.has_outdoor_space),
                int(listing.has_garage),
                int(listing.has_in_unit_laundry),
                listing.score,
                now,
                now,
                int(listing.is_active),
                int(listing.notified),
                listing.raw_amenities,
            ),
        )
        conn.commit()
        conn.close()
        return True


def get_new_listings(db_path: str = DB_PATH) -> list[Listing]:
    """Get all listings that haven't been notified yet."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM listings WHERE notified = 0 AND is_active = 1 ORDER BY score DESC"
    ).fetchall()
    conn.close()
    return [_row_to_listing(row) for row in rows]


def mark_notified(listing_ids: list[str], db_path: str = DB_PATH) -> None:
    """Mark listings as notified."""
    if not listing_ids:
        return
    conn = get_connection(db_path)
    placeholders = ",".join("?" for _ in listing_ids)
    conn.execute(
        f"UPDATE listings SET notified = 1 WHERE listing_id IN ({placeholders})",
        listing_ids,
    )
    conn.commit()
    conn.close()


def get_all_active_ranked(db_path: str = DB_PATH) -> list[Listing]:
    """Get all active listings sorted by score descending."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM listings WHERE is_active = 1 ORDER BY score DESC"
    ).fetchall()
    conn.close()
    return [_row_to_listing(row) for row in rows]


def get_stats(db_path: str = DB_PATH) -> dict:
    """Get summary statistics."""
    conn = get_connection(db_path)
    total = conn.execute(
        "SELECT COUNT(*) FROM listings WHERE is_active = 1"
    ).fetchone()[0]
    by_source = conn.execute(
        "SELECT source, COUNT(*) FROM listings WHERE is_active = 1 GROUP BY source"
    ).fetchall()
    conn.close()
    return {
        "total_active": total,
        "by_source": {row[0]: row[1] for row in by_source},
    }


def _row_to_listing(row: sqlite3.Row) -> Listing:
    """Convert a database row to a Listing object."""
    listing = Listing(
        source=row["source"],
        source_url=row["source_url"],
        source_listing_id=row["source_listing_id"],
        title=row["title"],
        address=row["address"],
        neighborhood=row["neighborhood"],
        price=row["price"],
        bedrooms=row["bedrooms"],
        bathrooms=row["bathrooms"],
        sqft=row["sqft"],
        property_type=row["property_type"],
        has_outdoor_space=bool(row["has_outdoor_space"]),
        has_garage=bool(row["has_garage"]),
        has_in_unit_laundry=bool(row["has_in_unit_laundry"]),
        score=row["score"],
        first_seen=datetime.fromisoformat(row["first_seen"]),
        last_seen=datetime.fromisoformat(row["last_seen"]),
        is_active=bool(row["is_active"]),
        notified=bool(row["notified"]),
        raw_amenities=row["raw_amenities"],
    )
    return listing
