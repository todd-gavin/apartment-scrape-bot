"""Email notifications via Resend."""

import logging
from datetime import datetime

import resend

from models import Listing
from config import RESEND_API_KEY, EMAIL_FROM, EMAIL_TO
from database import get_stats

logger = logging.getLogger(__name__)


def send_new_listings_email(listings: list[Listing]) -> bool:
    """Send an HTML email with new listings, sorted by score.

    Returns True if email was sent successfully.
    """
    if not listings:
        logger.info("No new listings to notify about")
        return False

    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email notification")
        return False

    resend.api_key = RESEND_API_KEY

    stats = get_stats()
    subject = f"[Apt Bot] {len(listings)} New Listing{'s' if len(listings) != 1 else ''} Found - {datetime.now().strftime('%b %d, %Y')}"

    html = _build_html(listings, stats)

    try:
        result = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": EMAIL_TO,
            "subject": subject,
            "html": html,
        })
        logger.info(f"Email sent successfully: {result}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_test_email() -> bool:
    """Send a test email to verify Resend setup."""
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY not set")
        return False

    resend.api_key = RESEND_API_KEY

    try:
        result = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": EMAIL_TO,
            "subject": "[Apt Bot] Test Email - Setup Verified",
            "html": """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2d7d46;">Apartment Scrape Bot - Test Email</h2>
                <p>Your email notifications are set up correctly!</p>
                <p>You'll receive emails with new rental listings when the bot finds matches.</p>
                <p style="color: #666; font-size: 12px;">Sent by Apartment Scrape Bot</p>
            </div>
            """,
        })
        logger.info(f"Test email sent: {result}")
        return True
    except Exception as e:
        logger.error(f"Test email failed: {e}")
        return False


def _build_html(listings: list[Listing], stats: dict) -> str:
    """Build the HTML email body."""
    # Sort by score descending
    sorted_listings = sorted(listings, key=lambda x: x.score, reverse=True)

    top_score = sorted_listings[0].score if sorted_listings else 0

    rows = ""
    for l in sorted_listings:
        # Color-code the score
        if l.score >= 85:
            score_color = "#2d7d46"  # green
        elif l.score >= 65:
            score_color = "#3b82f6"  # blue
        elif l.score >= 45:
            score_color = "#f59e0b"  # amber
        else:
            score_color = "#ef4444"  # red

        # Price tier badge
        tier = l.price_tier()
        if tier == "Ideal":
            tier_color = "#2d7d46"
        elif tier == "Local Max":
            tier_color = "#f59e0b"
        elif tier == "Absolute Max":
            tier_color = "#ef4444"
        else:
            tier_color = "#9ca3af"

        amenities = l.amenity_summary()

        rows += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px 8px; text-align: center;">
                <span style="color: {score_color}; font-weight: bold; font-size: 18px;">{l.score}</span>
            </td>
            <td style="padding: 12px 8px;">
                <span style="background: {tier_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{tier}</span>
                <br><strong>${l.price:,}/mo</strong>
            </td>
            <td style="padding: 12px 8px;">{l.neighborhood or 'N/A'}</td>
            <td style="padding: 12px 8px;">{l.bedrooms}BR</td>
            <td style="padding: 12px 8px; font-size: 13px;">{amenities}</td>
            <td style="padding: 12px 8px;">
                <a href="{l.source_url}" style="color: #3b82f6; text-decoration: none;">View →</a>
                <br><span style="font-size: 11px; color: #9ca3af;">{l.source}</span>
            </td>
        </tr>
        """

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; background: #f9fafb; padding: 20px;">
        <div style="background: white; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
            <h1 style="color: #1f2937; margin: 0 0 8px 0; font-size: 22px;">
                Apartment Scrape Bot
            </h1>
            <p style="color: #6b7280; margin: 0;">
                {len(listings)} new listing{'s' if len(listings) != 1 else ''} found
                &middot; Top score: {top_score}
                &middot; {stats.get('total_active', 'N/A')} total active
            </p>
        </div>

        <div style="background: white; border-radius: 8px; overflow: hidden;">
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #f3f4f6; border-bottom: 2px solid #e5e7eb;">
                        <th style="padding: 12px 8px; text-align: center; width: 60px;">Score</th>
                        <th style="padding: 12px 8px; text-align: left;">Price</th>
                        <th style="padding: 12px 8px; text-align: left;">Area</th>
                        <th style="padding: 12px 8px; text-align: left; width: 50px;">Beds</th>
                        <th style="padding: 12px 8px; text-align: left;">Amenities</th>
                        <th style="padding: 12px 8px; text-align: left; width: 80px;">Link</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>

        <div style="text-align: center; margin-top: 16px; color: #9ca3af; font-size: 12px;">
            <p>Searching: Santa Monica, Brentwood, Mar Vista, Ocean Park, Venice</p>
            <p>Budget: $3,100 ideal &middot; $3,500 local max &middot; $4,000 absolute max</p>
            <p>Sent by <a href="https://github.com/todd-gavin/apartment-scrape-bot" style="color: #6b7280;">Apartment Scrape Bot</a></p>
        </div>
    </div>
    """
    return html
