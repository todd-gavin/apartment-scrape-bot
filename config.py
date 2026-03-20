"""Central configuration for the apartment scrape bot."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Search Parameters ---
NEIGHBORHOODS = [
    "Santa Monica",
    "Brentwood",
    "Mar Vista",
    "Ocean Park",
    "Venice",
]

PRICE_IDEAL = 3100
PRICE_LOCAL_MAX = 3500
PRICE_ABSOLUTE_MAX = 4000
MIN_BEDROOMS = 1
MAX_BEDROOMS = 1

# --- Scoring Weights (must sum to 100) ---
SCORE_WEIGHTS = {
    "price": 35,
    "bedrooms": 20,
    "outdoor_space": 15,
    "garage": 15,
    "in_unit_laundry": 15,
}

# --- Amenity Detection Keywords ---
OUTDOOR_KEYWORDS = [
    "balcony", "patio", "deck", "terrace", "yard", "garden",
    "outdoor space", "rooftop", "courtyard",
]
GARAGE_KEYWORDS = [
    "garage", "enclosed parking", "private garage", "1-car garage",
    "one-car garage", "attached garage",
]
LAUNDRY_KEYWORDS = [
    "in-unit laundry", "in unit laundry", "washer/dryer in unit",
    "washer and dryer in unit", "in-unit washer", "w/d in unit",
    "washer dryer in unit", "in unit w/d", "in-unit w/d",
]

# --- Email (Resend) ---
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "Apartment Bot <onboarding@resend.dev>")
EMAIL_TO = os.getenv("EMAIL_TO", "toddgavin@gmail.com")

# --- Database ---
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "listings.db")

# --- Session Log ---
SESSION_LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "session_log.md")

# --- Scraper Settings ---
REQUEST_DELAY_MIN = 3  # seconds
REQUEST_DELAY_MAX = 8
PLAYWRIGHT_TIMEOUT = 30000  # ms
MAX_RETRIES = 2

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# --- Craigslist ---
CRAIGSLIST_BASE_URL = "https://losangeles.craigslist.org/search/wst/apa"
CRAIGSLIST_PARAMS = {
    "min_price": 0,
    "max_price": PRICE_ABSOLUTE_MAX,
    "min_bedrooms": MIN_BEDROOMS,
    "max_bedrooms": MAX_BEDROOMS,
}

# --- Apartments.com ---
APARTMENTS_COM_SEARCH_URLS = [
    "https://www.apartments.com/santa-monica-ca/1-bedrooms/under-4000/",
    "https://www.apartments.com/brentwood-los-angeles-ca/1-bedrooms/under-4000/",
    "https://www.apartments.com/mar-vista-los-angeles-ca/1-bedrooms/under-4000/",
    "https://www.apartments.com/venice-los-angeles-ca/1-bedrooms/under-4000/",
]

# --- Zillow ---
ZILLOW_SEARCH_URLS = [
    "https://www.zillow.com/santa-monica-ca/rentals/1-_beds/?searchQueryState=%7B%22isMapVisible%22%3Atrue%2C%22filterState%22%3A%7B%22price%22%3A%7B%22max%22%3A4000%7D%2C%22beds%22%3A%7B%22min%22%3A1%2C%22max%22%3A1%7D%2C%22fr%22%3A%7B%22value%22%3Atrue%7D%2C%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%7D%7D",
]

# --- Zumper ---
ZUMPER_SEARCH_URLS = [
    "https://www.zumper.com/apartments-for-rent/santa-monica-ca?beds=1&price_max=4000",
    "https://www.zumper.com/apartments-for-rent/los-angeles-ca/brentwood?beds=1&price_max=4000",
    "https://www.zumper.com/apartments-for-rent/los-angeles-ca/mar-vista?beds=1&price_max=4000",
    "https://www.zumper.com/apartments-for-rent/los-angeles-ca/venice?beds=1&price_max=4000",
]

# --- HotPads ---
HOTPADS_SEARCH_URLS = [
    "https://hotpads.com/santa-monica-ca/apartments-for-rent?price=0-4000&beds=1",
    "https://hotpads.com/venice-ca/apartments-for-rent?price=0-4000&beds=1",
]

# --- WestsideRentals ---
WESTSIDERENTALS_SEARCH_URLS = [
    "https://www.westsiderentals.com/santa-monica-ca/apartments-for-rent?bedrooms=1&price_max=4000",
]
