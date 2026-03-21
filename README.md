# Apartment Scrape Bot

Automated rental listing scraper that monitors 6 major housing sites for apartments and houses near Santa Monica, CA. Runs autonomously on GitHub Actions, scores listings by how well they match your preferences, and sends email alerts when new matches are found.

## How It Works

```
Scrape 6 sites  →  Score & rank listings  →  Store in SQLite  →  Email new finds
     ↑                                                                    |
     └──────────── GitHub Actions cron (5x daily) ────────────────────────┘
```

Every run:
1. Scrapes Craigslist, Apartments.com, Zillow, Zumper, HotPads, and WestsideRentals
2. Filters to target neighborhoods and budget
3. Detects amenities (garage, outdoor space, in-unit laundry) from listing text
4. Scores each listing 0-100 based on preference match
5. Deduplicates against previously seen listings
6. Emails only **new** listings, sorted by score
7. Logs session results to `logs/session_log.md`

## Search Parameters

| Parameter | Value |
|-----------|-------|
| **Neighborhoods** | Santa Monica, Brentwood, Mar Vista, Ocean Park, Venice |
| **Ideal budget** | $3,100/mo |
| **Local max** | $3,500/mo |
| **Absolute max** | $4,000/mo |
| **Bedrooms** | 1 |
| **Preferred amenities** | Outdoor space, enclosed garage, in-unit laundry |

All parameters are configurable in `config.py`.

## Live Dashboard

A mobile-friendly dashboard is auto-generated after each scrape and deployed via GitHub Pages:

**https://todd-gavin.github.io/apartment-scrape-bot/**

Features:
- Sortable table (click any column header)
- Filter by neighborhood and price tier
- Color-coded scores and amenity badges
- Direct links to each listing on the source site
- Mobile-responsive — works great on phones

The dashboard updates automatically 5x daily with each scheduled scrape.

## Scoring System

Each listing is scored on a 0-100 scale:

| Component | Points | Logic |
|-----------|--------|-------|
| Price | 35 | Full points at/under $3,100; linear decay to $4,000; 0 if over |
| Bedrooms | 20 | 1BR = 20, 2BR = 10, other = 5 |
| Outdoor space | 15 | Deck, patio, balcony, yard, terrace |
| Garage | 15 | Enclosed or private garage |
| In-unit laundry | 15 | Washer/dryer in unit |

**Score tiers:** 85-100 = Dream listing, 65-84 = Strong match, 45-64 = Decent option, <45 = Marginal

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/todd-gavin/apartment-scrape-bot.git
cd apartment-scrape-bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure email

Sign up at [resend.com](https://resend.com) (free tier) and get an API key.

```bash
cp .env.example .env
# Edit .env and add your RESEND_API_KEY
```

### 3. Run locally

```bash
# Verify email setup
python main.py --test-email

# Dry run (scrape + score, no email)
python main.py --dry-run

# Full run
python main.py

# Single scraper only
python main.py --source craigslist --dry-run
```

### 4. Deploy to GitHub Actions

1. Push this repo to GitHub
2. Go to **Settings > Secrets and variables > Actions**
3. Add secret: `RESEND_API_KEY` = your Resend API key
4. Go to **Settings > Pages** > Source: "Deploy from a branch" > Branch: `main` > Folder: `/docs`
5. The bot will run automatically at **8am, 11am, 2pm, 5pm, and 8pm Pacific** daily
6. Dashboard live at `https://todd-gavin.github.io/apartment-scrape-bot/`
7. You can also trigger it manually from the **Actions** tab

## Project Structure

```
apartment-scrape-bot/
├── main.py                  # Entry point (scrape → score → notify → log)
├── generate_dashboard.py    # Generates docs/index.html from listings DB
├── config.py                # Search params, scoring weights, URLs
├── models.py                # Listing dataclass
├── database.py              # SQLite persistence layer
├── scorer.py                # 0-100 preferability scoring
├── notifier.py              # Resend HTML email notifications
├── session_log.py           # Session logging to markdown
├── scrapers/
│   ├── base.py              # Abstract base (retry, rate limiting, stealth)
│   ├── craigslist.py        # httpx + BeautifulSoup
│   ├── apartments_com.py    # Playwright
│   ├── zillow.py            # Playwright + __NEXT_DATA__ JSON
│   ├── zumper.py            # Playwright
│   ├── hotpads.py           # Playwright
│   └── westsiderentals.py   # Extends apartments_com
├── docs/
│   └── index.html           # Generated dashboard (GitHub Pages)
├── data/
│   └── listings.db          # SQLite database (persisted in repo)
├── logs/
│   └── session_log.md       # Append-only session history
├── tests/                   # pytest suite (28 tests)
├── .github/workflows/
│   └── scrape.yml           # GitHub Actions cron schedule
├── requirements.txt
└── .env.example
```

## Scrapers

| Site | Method | Anti-Bot Handling |
|------|--------|-------------------|
| Craigslist | httpx + BeautifulSoup | User-agent rotation, rate limiting |
| Apartments.com | Playwright | Stealth plugin, random delays |
| Zillow | Playwright | `__NEXT_DATA__` JSON parsing, stealth |
| Zumper | Playwright | Stealth plugin, scroll loading |
| HotPads | Playwright | Stealth plugin, scroll loading |
| WestsideRentals | Playwright | Shares Apartments.com backend |

All Playwright scrapers use [playwright-stealth](https://github.com/nichochar/playwright-stealth) to avoid detection, randomized user agents, and 3-10 second delays between requests. If a scraper fails, the others continue — results are never all-or-nothing.

## Email Notifications

New listings arrive as a styled HTML email with a ranked table:

| Score | Price | Area | Beds | Amenities | Link |
|-------|-------|------|------|-----------|------|
| 99.7 | $3,108/mo | Santa Monica | 1BR | Outdoor, Garage, In-Unit W/D | [View →]() |
| 85.0 | $2,495/mo | Venice | 1BR | Outdoor, In-Unit W/D | [View →]() |

Emails are only sent when **new** listings are found. No spam on quiet days.

## Running Tests

```bash
python -m pytest tests/ -v
```

28 tests covering scoring logic, database operations, and email HTML generation.

## Customizing

To adapt this bot for a different search:

1. Edit `config.py` — change `NEIGHBORHOODS`, `PRICE_*` values, and search URLs
2. Edit `config.py` — adjust `SCORE_WEIGHTS` and amenity keywords
3. Edit `.env` — set your `EMAIL_TO` recipient
4. Push to GitHub and add your `RESEND_API_KEY` secret

## License

MIT
