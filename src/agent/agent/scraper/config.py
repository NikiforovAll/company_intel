"""Crawling configuration — all tunable parameters in one place."""

from __future__ import annotations

# -- Website deep crawl (homepage BFS) --
WEBSITE_MAX_DEPTH = 2
WEBSITE_MAX_PAGES = 20

# -- Company pages shallow crawl (newsroom, about, blog) --
COMPANY_PAGES_MAX_DEPTH = 1
COMPANY_PAGES_MAX_PAGES = 10
COMPANY_PAGES_MAX_SEEDS = 5

# -- Search results scrape --
SEARCH_MAX_URLS = 10
SEARCH_PER_URL_TIMEOUT = 45  # seconds
SEARCH_BATCH_TIMEOUT = 300  # seconds

# -- Shared crawl settings --
PAGE_TIMEOUT_MS = 30_000
MEAN_DELAY = 1.0  # seconds between requests
DELAY_JITTER = 0.5  # ± range around mean_delay
EXCLUDED_TAGS = ["nav", "footer", "header", "aside", "form"]

# -- Wikipedia --
WIKIPEDIA_MAX_RETRIES = 3
WIKIPEDIA_RELATED_LIMIT = 4  # extra articles whose title contains the company name
WIKIPEDIA_CSS_SELECTOR = "div#mw-content-text"
WIKIPEDIA_EXCLUDED_SELECTOR = ".reflist, .navbox, .hatnote, .sidebar, .infobox"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_USER_AGENT = (
    "CompanyIntelBot/1.0 (https://github.com/nikiforovall/company_intel)"
)

# -- DuckDuckGo search --
DDG_MAX_RESULTS = 10
DDG_SEARCH_QUERIES = [
    "{company} company",
    "{company} about company overview",
    "{company} company news products",
]

# -- URL filtering --
SKIP_DOMAINS = {
    "wikipedia.org",
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "linkedin.com",
    "tiktok.com",
    "reddit.com",
    "msn.com",
}

ABOUT_KEYWORDS = {"about", "company", "newsroom", "press", "investors", "who-we-are"}

# -- Subdomain probing --
PROBE_SUBDOMAINS = [
    "newsroom",
    "about",
    "blog",
    "press",
    "investors",
    "engineering",
    "news",
]
PROBE_TIMEOUT = 5  # seconds
