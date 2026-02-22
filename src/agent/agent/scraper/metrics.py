from __future__ import annotations

from opentelemetry import metrics

meter = metrics.get_meter("company-intel.scraper")

pages_scraped = meter.create_counter(
    "scraper.pages_scraped",
    description="Total pages successfully scraped",
)

pages_dropped = meter.create_counter(
    "scraper.pages_dropped",
    description="Pages dropped during content filtering",
)

scrape_errors = meter.create_counter(
    "scraper.errors",
    description="Scraping errors by type and phase",
)

phase_duration = meter.create_histogram(
    "scraper.phase_duration",
    description="Duration of pipeline phases",
    unit="s",
)

page_content_size = meter.create_histogram(
    "scraper.page_content_size",
    description="Size of scraped page content after cleaning",
    unit="By",
)

active_browsers = meter.create_up_down_counter(
    "scraper.active_browsers",
    description="Currently active browser sessions",
)
