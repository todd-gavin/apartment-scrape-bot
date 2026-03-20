"""Apartment Scrape Bot — Entry point.

Usage:
    python main.py                  # Full run: scrape + score + email
    python main.py --dry-run        # Scrape + score, no email
    python main.py --source NAME    # Run single scraper only
    python main.py --test-email     # Send test email to verify setup
"""

import argparse
import asyncio
import logging
import sys
import time

from config import PRICE_ABSOLUTE_MAX
from database import init_db, upsert_listing, get_new_listings, mark_notified, get_stats
from scorer import compute_score
from notifier import send_new_listings_email, send_test_email
from session_log import log_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_scraper(scraper_class) -> tuple[list, dict]:
    """Run a single scraper and return (listings, status)."""
    scraper = scraper_class()
    results = await scraper.run()
    status = scraper.get_status()
    return results, status


async def main(args):
    start_time = time.time()

    # Handle test email
    if args.test_email:
        success = send_test_email()
        sys.exit(0 if success else 1)

    # Initialize database
    init_db()

    # Import scrapers
    from scrapers import ALL_SCRAPERS

    # Determine which scrapers to run
    if args.source:
        if args.source not in ALL_SCRAPERS:
            logger.error(f"Unknown source: {args.source}. Available: {', '.join(ALL_SCRAPERS.keys())}")
            sys.exit(1)
        scrapers_to_run = {args.source: ALL_SCRAPERS[args.source]}
    else:
        scrapers_to_run = ALL_SCRAPERS

    # Run scrapers
    all_listings = []
    scraper_statuses = []

    for name, scraper_class in scrapers_to_run.items():
        logger.info(f"--- Running {name} scraper ---")
        try:
            listings, status = await run_scraper(scraper_class)

            # Filter out over-budget listings
            listings = [l for l in listings if l.price <= PRICE_ABSOLUTE_MAX or l.price == 0]

            # Score each listing
            for listing in listings:
                listing.score = compute_score(listing)

            all_listings.extend(listings)
            scraper_statuses.append(status)
        except Exception as e:
            logger.error(f"Scraper {name} failed: {e}")
            scraper_statuses.append({
                "source": name,
                "status": "FAILED",
                "found": 0,
                "errors": 1,
                "error_messages": [str(e)],
            })

    # Upsert listings into database
    new_count = 0
    for listing in all_listings:
        is_new = upsert_listing(listing)
        if is_new:
            new_count += 1

    # Update scraper statuses with new counts
    new_by_source = {}
    for listing in all_listings:
        new_by_source.setdefault(listing.source, 0)
    for status in scraper_statuses:
        status["new"] = new_by_source.get(status["source"], 0)

    logger.info(f"Total listings scraped: {len(all_listings)}, New: {new_count}")

    # Get new listings for notification
    new_listings = get_new_listings()
    stats = get_stats()

    # Send email notification
    email_sent = False
    if not args.dry_run and new_listings:
        email_sent = send_new_listings_email(new_listings)
        if email_sent:
            mark_notified([l.listing_id for l in new_listings])
            logger.info(f"Notified about {len(new_listings)} new listings")
    elif args.dry_run:
        logger.info(f"[DRY RUN] Would have emailed {len(new_listings)} new listings")

    # Top listing for logging
    top_listing = ""
    if new_listings:
        top = new_listings[0]
        top_listing = f"Score {top.score} - ${top.price:,} {top.bedrooms}BR {top.neighborhood}"

    # Log session
    duration = time.time() - start_time
    log_session(
        duration_seconds=duration,
        scraper_results=scraper_statuses,
        new_count=new_count,
        total_active=stats.get("total_active", 0),
        email_sent=email_sent,
        top_listing=top_listing,
    )

    logger.info(f"Done in {duration:.1f}s. Active listings: {stats.get('total_active', 0)}")


def parse_args():
    parser = argparse.ArgumentParser(description="Apartment Scrape Bot")
    parser.add_argument("--dry-run", action="store_true", help="Scrape and score but don't send email")
    parser.add_argument("--source", type=str, help="Run only a specific scraper (e.g., craigslist)")
    parser.add_argument("--test-email", action="store_true", help="Send a test email and exit")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
