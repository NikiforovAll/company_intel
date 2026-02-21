from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from urllib.parse import quote, urlparse

import httpx
import logfire
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
)
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import ContentTypeFilter, FilterChain
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException

from agent.scraper._compat import run_in_crawler_thread
from agent.scraper.cleaner import clean_text, is_english
from agent.scraper.config import (
    ABOUT_KEYWORDS,
    COMPANY_PAGES_MAX_DEPTH,
    COMPANY_PAGES_MAX_PAGES,
    COMPANY_PAGES_MAX_SEEDS,
    DDG_MAX_RESULTS,
    DDG_SEARCH_QUERIES,
    DELAY_JITTER,
    EXCLUDED_TAGS,
    MEAN_DELAY,
    PAGE_TIMEOUT_MS,
    PROBE_SUBDOMAINS,
    PROBE_TIMEOUT,
    SEARCH_BATCH_TIMEOUT,
    SEARCH_MAX_URLS,
    SEARCH_PER_URL_TIMEOUT,
    SKIP_DOMAINS,
    WEBSITE_MAX_DEPTH,
    WEBSITE_MAX_PAGES,
    WIKIPEDIA_API,
    WIKIPEDIA_CSS_SELECTOR,
    WIKIPEDIA_EXCLUDED_SELECTOR,
    WIKIPEDIA_MAX_RETRIES,
    WIKIPEDIA_USER_AGENT,
)
from agent.scraper.models import RawDocument, SearchResults, SourceType, WikipediaResult

logger = logging.getLogger(__name__)

BROWSER_CONFIG = BrowserConfig(headless=True)

MARKDOWN_GENERATOR = DefaultMarkdownGenerator(
    options={"ignore_links": True},
)

_WIKIPEDIA_HEADERS = {"User-Agent": WIKIPEDIA_USER_AGENT}
_WIKIPEDIA_INFOBOX_URL_RE = re.compile(
    r'class="url"[^>]*><a\s+[^>]*href="([^"]+)"', re.IGNORECASE
)


def _extract_fit_markdown(result: object) -> str | None:
    md = getattr(result, "markdown", None)
    if md is None:
        return None
    if hasattr(md, "fit_markdown") and md.fit_markdown:
        return str(md.fit_markdown)
    if isinstance(md, str):
        return md
    raw = getattr(md, "raw_markdown", None)
    return str(raw) if raw else None


def _build_bfs_config(max_depth: int, max_pages: int) -> CrawlerRunConfig:
    return CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            max_pages=max_pages,
            include_external=False,
            filter_chain=FilterChain(
                [ContentTypeFilter(allowed_types=["text/html"], check_extension=True)]
            ),
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=MARKDOWN_GENERATOR,
        excluded_tags=EXCLUDED_TAGS,
        check_robots_txt=True,
        page_timeout=PAGE_TIMEOUT_MS,
        mean_delay=MEAN_DELAY,
        max_range=DELAY_JITTER,
        cache_mode=CacheMode.BYPASS,
    )


def _build_wikipedia_config() -> CrawlerRunConfig:
    return CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=MARKDOWN_GENERATOR,
        excluded_tags=EXCLUDED_TAGS,
        css_selector=WIKIPEDIA_CSS_SELECTOR,
        excluded_selector=WIKIPEDIA_EXCLUDED_SELECTOR,
        check_robots_txt=True,
        page_timeout=PAGE_TIMEOUT_MS,
        cache_mode=CacheMode.BYPASS,
    )


# --- Raw browser operations (run in crawler thread) ---


async def _crawl_pages(url: str, config: CrawlerRunConfig) -> list[object]:
    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        results = await crawler.arun(url=url, config=config)
        return results if isinstance(results, list) else [results]


async def _crawl_single_with_retry(
    url: str, config: CrawlerRunConfig, max_retries: int = WIKIPEDIA_MAX_RETRIES
) -> object:
    delay = 1.0
    last_result = None
    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        for attempt in range(max_retries):
            result = await crawler.arun(url=url, config=config)
            if getattr(result, "success", False):
                return result
            last_result = result
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
    return last_result  # type: ignore[return-value]


async def _crawl_urls_sequentially(
    urls: list[str], config: CrawlerRunConfig
) -> list[tuple[str, object]]:
    results: list[tuple[str, object]] = []
    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        for url in urls[:SEARCH_MAX_URLS]:
            try:
                result = await asyncio.wait_for(
                    crawler.arun(url=url, config=config),
                    timeout=SEARCH_PER_URL_TIMEOUT,
                )
                results.append((url, result))
            except TimeoutError:
                logger.warning("Timeout scraping %s, skipping", url)
            await asyncio.sleep(MEAN_DELAY)
    return results


# --- Public functions (OTel spans + processing on main loop) ---


def _process_crawl_result(
    result: object,
    url: str,
    source_type: SourceType,
    company: str,
    now: datetime,
) -> RawDocument | None:
    raw_md = _extract_fit_markdown(result)
    if not raw_md:
        logger.debug("No markdown for %s", url)
        return None

    cleaned = clean_text(raw_md)
    if cleaned is None:
        logger.debug("Content too short for %s (%d raw chars)", url, len(raw_md))
        return None

    if not is_english(cleaned):
        logger.debug("Non-English content for %s", url)
        return None

    title = ""
    meta = getattr(result, "metadata", None)
    if isinstance(meta, dict):
        title = meta.get("title", "")
    if not title:
        title = url

    return RawDocument(
        url=url,
        title=title,
        content=cleaned,
        source_type=source_type,
        company=company,
        scraped_at=now,
    )


async def scrape_website(url: str, company: str) -> tuple[list[RawDocument], list[str]]:
    documents: list[RawDocument] = []
    errors: list[str] = []
    now = datetime.now(UTC)

    with logfire.span("scrape_website {company}", company=company, url=url) as span:
        try:
            config = _build_bfs_config(WEBSITE_MAX_DEPTH, WEBSITE_MAX_PAGES)
            items = await run_in_crawler_thread(lambda: _crawl_pages(url, config))

            for result in items:
                page_url = getattr(result, "url", url)
                if not getattr(result, "success", False):
                    err_msg = getattr(result, "error_message", "Unknown error")
                    errors.append(f"{page_url}: {err_msg}")
                    continue

                doc = _process_crawl_result(result, page_url, "website", company, now)
                if doc:
                    documents.append(doc)
        except asyncio.CancelledError:
            logger.warning("Website scrape cancelled for %s", url)
            errors.append(f"Website scrape cancelled for {url}")
        except Exception:
            logger.exception("Website scrape failed for %s", url)
            errors.append(f"Website scrape failed for {url}")

        span.set_attribute("pages_scraped", len(documents))
        span.set_attribute("error_count", len(errors))

    return documents, errors


async def scrape_company_pages(
    urls: list[str],
    company: str,
    seen_urls: set[str] | None = None,
) -> tuple[list[RawDocument], list[str]]:
    """Shallow BFS crawl of company pages (about, newsroom, blog)."""
    documents: list[RawDocument] = []
    errors: list[str] = []
    now = datetime.now(UTC)
    seen = seen_urls if seen_urls is not None else set()

    if not urls:
        return documents, errors

    logger.info("Crawling %d company pages for %s: %s", len(urls), company, urls)

    with logfire.span(
        "scrape_company_pages {company}",
        company=company,
        url_count=len(urls),
    ) as span:
        config = _build_bfs_config(COMPANY_PAGES_MAX_DEPTH, COMPANY_PAGES_MAX_PAGES)
        for url in urls[:COMPANY_PAGES_MAX_SEEDS]:
            if url in seen:
                continue
            try:
                items = await run_in_crawler_thread(
                    lambda u=url: _crawl_pages(u, config)  # type: ignore[misc]
                )
                for result in items:
                    page_url = getattr(result, "url", url)
                    if page_url in seen:
                        continue
                    seen.add(page_url)
                    if not getattr(result, "success", False):
                        err = getattr(result, "error_message", "Unknown")
                        errors.append(f"{page_url}: {err}")
                        continue
                    doc = _process_crawl_result(
                        result, page_url, "website", company, now
                    )
                    if doc:
                        documents.append(doc)
            except asyncio.CancelledError:
                logger.warning("Company page crawl cancelled for %s", url)
                errors.append(f"Company page crawl cancelled for {url}")
                break
            except Exception:
                logger.exception("Company page crawl failed for %s", url)
                errors.append(f"Company page crawl failed for {url}")

        span.set_attribute("pages_scraped", len(documents))
        span.set_attribute("error_count", len(errors))

    return documents, errors


async def _wikipedia_search(company: str) -> str | None:
    params: dict[str, str | int] = {
        "action": "query",
        "list": "search",
        "srsearch": f"{company} company",
        "format": "json",
        "srlimit": 1,
    }
    async with httpx.AsyncClient(timeout=15, headers=_WIKIPEDIA_HEADERS) as client:
        resp = await client.get(WIKIPEDIA_API, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = data.get("query", {}).get("search", [])
    if not results:
        return None
    return str(results[0]["title"])


async def _wikipedia_official_url(title: str) -> str | None:
    params: dict[str, str | int] = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "section": 0,
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=15, headers=_WIKIPEDIA_HEADERS) as client:
        resp = await client.get(WIKIPEDIA_API, params=params)
        resp.raise_for_status()
        data = resp.json()

    html = data.get("parse", {}).get("text", {}).get("*", "")
    match = _WIKIPEDIA_INFOBOX_URL_RE.search(html)
    if match:
        url = match.group(1)
        if url.startswith("//"):
            url = "https:" + url
        return url
    return None


def _is_social_or_wiki(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return any(skip in domain for skip in SKIP_DOMAINS)


def _extract_root_domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _is_same_company(url: str, root_domain: str) -> bool:
    return _extract_root_domain(url) == root_domain


def _is_homepage(url: str, root_domain: str) -> bool:
    parsed = urlparse(url)
    return _extract_root_domain(url) == root_domain and parsed.path.strip("/") == ""


def _collect_urls(
    ddgs: DDGS,
    queries: list[str],
    seen: set[str],
    max_results: int,
) -> list[str]:
    urls: list[str] = []
    for query in queries:
        try:
            results = ddgs.text(query, max_results=max_results)
        except DuckDuckGoSearchException:
            logger.warning("DDG search failed: %s", query)
            continue
        for r in results:
            url = str(r["href"])
            if url in seen or _is_social_or_wiki(url):
                continue
            seen.add(url)
            urls.append(url)
    return urls


def _collect_news(
    ddgs: DDGS, company: str, seen: set[str], max_results: int
) -> list[str]:
    urls: list[str] = []
    try:
        results = ddgs.news(f"{company} company", max_results=max_results)
    except DuckDuckGoSearchException:
        logger.warning("DDG news search failed for %s", company)
        return urls
    for r in results:
        url = str(r["url"])
        if url in seen or _is_social_or_wiki(url):
            continue
        seen.add(url)
        urls.append(url)
    return urls


async def probe_company_subdomains(homepage_url: str) -> list[str]:
    """HEAD-check common company subdomains to discover pages DDG misses."""
    root = _extract_root_domain(homepage_url)
    candidates = [f"https://{sub}.{root}" for sub in PROBE_SUBDOMAINS]

    found: list[str] = []
    async with httpx.AsyncClient(
        timeout=PROBE_TIMEOUT, follow_redirects=True, verify=False
    ) as client:
        for url in candidates:
            try:
                resp = await client.head(url)
                if resp.status_code < 400:
                    resolved = str(resp.url)
                    if _extract_root_domain(resolved) == root:
                        found.append(resolved)
            except Exception:
                pass
    if found:
        logger.info("Subdomain probe for %s found: %s", root, found)
    return found


def search_company(
    company: str,
    known_homepage: str | None = None,
    max_results: int = DDG_MAX_RESULTS,
) -> SearchResults:
    """Multi-query DDG search + news. Classifies URLs by company domain."""
    with logfire.span("search_company {company}", company=company) as span:
        seen: set[str] = set()
        ddgs = DDGS()

        queries = [q.format(company=company) for q in DDG_SEARCH_QUERIES]
        web_urls = _collect_urls(ddgs, queries, seen, max_results)
        news_urls = _collect_news(ddgs, company, seen, max_results)
        all_urls = web_urls + news_urls

        logger.info(
            "DDG raw for %s: %d web + %d news = %d unique",
            company,
            len(web_urls),
            len(news_urls),
            len(all_urls),
        )

        if not all_urls and not known_homepage:
            return SearchResults(homepage_url=None)

        homepage_url = known_homepage or all_urls[0]
        root_domain = _extract_root_domain(homepage_url)

        company_urls: list[str] = []
        extra_urls: list[str] = []
        for url in all_urls:
            if _is_homepage(url, root_domain):
                continue
            if _is_same_company(url, root_domain):
                company_urls.append(url)
            else:
                extra_urls.append(url)

        company_urls.sort(
            key=lambda u: any(k in u.lower() for k in ABOUT_KEYWORDS),
            reverse=True,
        )

        logger.info(
            "DDG for %s: homepage=%s, company=%d, extra=%d",
            company,
            homepage_url,
            len(company_urls),
            len(extra_urls),
        )
        span.set_attribute("homepage_url", homepage_url)
        span.set_attribute("company_url_count", len(company_urls))
        span.set_attribute("extra_url_count", len(extra_urls))
        return SearchResults(
            homepage_url=homepage_url,
            company_urls=company_urls,
            extra_urls=extra_urls,
        )


async def scrape_search_results(
    urls: list[str], company: str
) -> tuple[list[RawDocument], list[str]]:
    """Scrape individual search result pages (no deep crawl)."""
    documents: list[RawDocument] = []
    errors: list[str] = []
    now = datetime.now(UTC)

    if not urls:
        return documents, errors

    logger.info("Scraping %d URLs for %s: %s", len(urls), company, urls[:5])

    with logfire.span(
        "scrape_search_results {company}",
        company=company,
        url_count=len(urls),
    ) as span:
        config = CrawlerRunConfig(
            scraping_strategy=LXMLWebScrapingStrategy(),
            markdown_generator=MARKDOWN_GENERATOR,
            excluded_tags=EXCLUDED_TAGS,
            check_robots_txt=True,
            page_timeout=PAGE_TIMEOUT_MS,
            cache_mode=CacheMode.BYPASS,
        )

        try:
            crawl_results = await asyncio.wait_for(
                run_in_crawler_thread(lambda: _crawl_urls_sequentially(urls, config)),
                timeout=SEARCH_BATCH_TIMEOUT,
            )

            for url, result in crawl_results:
                if not getattr(result, "success", False):
                    err = getattr(result, "error_message", "Unknown")
                    logger.warning("Scrape failed %s: %s", url, err)
                    errors.append(f"{url}: {err}")
                    continue

                doc = _process_crawl_result(result, url, "search", company, now)
                if doc:
                    documents.append(doc)
                else:
                    logger.info("No usable content from %s", url)
        except (TimeoutError, asyncio.CancelledError):
            logger.warning("Search results scrape timed out for %s", company)
            errors.append(f"Search results scrape timed out for {company}")
        except Exception:
            logger.exception("Search results scrape failed for %s", company)
            errors.append(f"Search results scrape failed for {company}")

        span.set_attribute("pages_scraped", len(documents))
        span.set_attribute("error_count", len(errors))

    return documents, errors


async def scrape_wikipedia(company: str) -> WikipediaResult:
    with logfire.span("scrape_wikipedia {company}", company=company) as span:
        title = await _wikipedia_search(company)
        if title is None:
            logger.info("No Wikipedia article found for %s", company)
            span.set_attribute("found", False)
            return WikipediaResult(document=None, official_website=None)

        span.set_attribute("article_title", title)

        official_url: str | None = None
        try:
            official_url = await _wikipedia_official_url(title)
        except Exception:
            logger.exception("Failed to extract official URL from Wikipedia infobox")

        if official_url:
            span.set_attribute("official_website", official_url)

        wiki_url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
        now = datetime.now(UTC)

        try:
            config = _build_wikipedia_config()
            result = await run_in_crawler_thread(
                lambda: _crawl_single_with_retry(wiki_url, config)
            )

            if not getattr(result, "success", False):
                err = getattr(result, "error_message", "Unknown")
                logger.warning("Wikipedia scrape failed for %s: %s", wiki_url, err)
                span.set_attribute("found", False)
                return WikipediaResult(document=None, official_website=official_url)

            doc = _process_crawl_result(result, wiki_url, "wikipedia", company, now)
            if doc:
                doc.title = title

            span.set_attribute("found", doc is not None)
            return WikipediaResult(document=doc, official_website=official_url)

        except Exception:
            logger.exception("Wikipedia scrape failed for %s", company)
            span.set_attribute("found", False)
            return WikipediaResult(document=None, official_website=official_url)
