"""Scrapers package — one module per rental site."""

from scrapers.craigslist import CraigslistScraper
from scrapers.apartments_com import ApartmentsComScraper
from scrapers.zillow import ZillowScraper
from scrapers.zumper import ZumperScraper
from scrapers.hotpads import HotPadsScraper
from scrapers.westsiderentals import WestsideRentalsScraper

ALL_SCRAPERS = {
    "craigslist": CraigslistScraper,
    "apartments.com": ApartmentsComScraper,
    "zillow": ZillowScraper,
    "zumper": ZumperScraper,
    "hotpads": HotPadsScraper,
    "westsiderentals": WestsideRentalsScraper,
}
