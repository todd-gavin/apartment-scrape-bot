"""Session logging — append structured markdown to logs/session_log.md."""

import logging
from datetime import datetime

from config import SESSION_LOG_PATH

logger = logging.getLogger(__name__)


def log_session(
    duration_seconds: float,
    scraper_results: list[dict],
    new_count: int,
    total_active: int,
    email_sent: bool,
    top_listing: str = "",
) -> None:
    """Append a session entry to the session log file."""
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S %Z").strip()

    # Format duration
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    # Overall status
    all_ok = all(r.get("status") == "OK" for r in scraper_results)
    any_ok = any(r.get("status") == "OK" for r in scraper_results)
    if all_ok:
        status = "Completed"
    elif any_ok:
        status = "Partial"
    else:
        status = "Failed"

    # Build scraper results table
    table_rows = ""
    for r in scraper_results:
        new = r.get("new", 0)
        table_rows += (
            f"| {r['source']} | {r['status']} | {r['found']} | {new} | {r['errors']} |\n"
        )

    # Build error details
    error_details = ""
    for r in scraper_results:
        for msg in r.get("error_messages", []):
            error_details += f"- {msg}\n"

    entry = f"""
## Session: {timestamp}

**Duration:** {duration_str} | **Status:** {status}

| Source | Status | Found | New | Errors |
|--------|--------|-------|-----|--------|
{table_rows}
**New listings:** {new_count} | **Total active:** {total_active} | **Email sent:** {"Yes" if email_sent else "No"}
"""

    if top_listing:
        entry += f"\n**Top new listing:** {top_listing}\n"

    if error_details:
        entry += f"\n### Errors\n{error_details}\n"

    entry += "\n---\n"

    try:
        with open(SESSION_LOG_PATH, "a") as f:
            f.write(entry)
        logger.info(f"Session logged to {SESSION_LOG_PATH}")
    except Exception as e:
        logger.error(f"Failed to write session log: {e}")
