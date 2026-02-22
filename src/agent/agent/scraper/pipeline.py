from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import logfire

from agent.scraper.crawl import (
    probe_company_subdomains,
    scrape_company_pages,
    scrape_search_results,
    scrape_website,
    scrape_wikipedia,
    search_company,
)
from agent.scraper.metrics import phase_duration
from agent.scraper.models import RawDocument, ScrapeResult
from agent.scraper.storage import save_raw_documents, wipe_raw_data

logger = logging.getLogger(__name__)


def _normalize_company(name: str) -> str:
    return name.strip().lower()


async def _empty_scrape_result() -> tuple[list[RawDocument], list[str]]:
    return [], []


async def scrape_company(
    company: str,
    data_dir: Path,
) -> ScrapeResult:
    company = _normalize_company(company)

    with logfire.span("scrape_company {company}", company=company) as span:
        wipe_raw_data(company, data_dir)

        all_docs: list[RawDocument] = []
        all_errors: list[str] = []
        seen_urls: set[str] = set()

        # --- Phase 1: Wikipedia + DDG search in parallel ---
        t0 = time.monotonic()
        wiki_result, search_results = await asyncio.gather(
            scrape_wikipedia(company),
            asyncio.to_thread(search_company, company),
        )
        phase_duration.record(time.monotonic() - t0, {"phase": "discovery"})

        if wiki_result.document:
            all_docs.append(wiki_result.document)
            seen_urls.add(wiki_result.document.url)
        for related_doc in wiki_result.related_documents:
            all_docs.append(related_doc)
            seen_urls.add(related_doc.url)

        # Patch homepage from Wikipedia if DDG missed it
        if wiki_result.official_website and not search_results.homepage_url:
            search_results.homepage_url = wiki_result.official_website

        homepage_url = wiki_result.official_website or search_results.homepage_url
        span.set_attribute("homepage_url", homepage_url or "")

        # --- Phase 2: Website BFS + subdomain probing ---
        website_docs: list[RawDocument] = []
        if homepage_url:
            t1 = time.monotonic()
            website_docs, website_errors = await scrape_website(homepage_url, company)
            all_docs.extend(website_docs)
            all_errors.extend(website_errors)
            seen_urls.update(d.url for d in website_docs)
            phase_duration.record(time.monotonic() - t1, {"phase": "website_bfs"})

            probed = await probe_company_subdomains(homepage_url)
            for u in probed:
                if u not in seen_urls and u not in search_results.company_urls:
                    search_results.company_urls.append(u)
        else:
            logger.warning("No homepage URL found for %s", company)

        # --- Phase 3: Company pages + search results in parallel ---
        co_urls = [u for u in search_results.company_urls if u not in seen_urls]
        extra_urls = [u for u in search_results.extra_urls if u not in seen_urls]

        t2 = time.monotonic()
        co_result, search_result = await asyncio.gather(
            scrape_company_pages(co_urls, company, seen_urls)
            if co_urls
            else _empty_scrape_result(),
            scrape_search_results(extra_urls, company),
        )
        phase_duration.record(time.monotonic() - t2, {"phase": "pages_and_search"})

        co_docs, co_errors = co_result
        search_docs, search_errors = search_result
        all_docs.extend(co_docs)
        all_errors.extend(co_errors)
        all_docs.extend(search_docs)
        all_errors.extend(search_errors)

        saved = save_raw_documents(company, all_docs, data_dir)

        wiki_count = (1 if wiki_result.document else 0) + len(
            wiki_result.related_documents
        )
        result = ScrapeResult(
            company=company,
            website_pages=len(website_docs),
            search_pages=len(search_docs),
            wikipedia_scraped=wiki_result.document is not None,
            wikipedia_pages=wiki_count,
            total_documents=saved,
            errors=all_errors,
        )

        span.set_attribute("total_documents", saved)
        span.set_attribute("website_pages", len(website_docs))
        span.set_attribute("search_pages", len(search_docs))
        span.set_attribute("wikipedia_pages", wiki_count)
        span.set_attribute("wikipedia_scraped", wiki_result.document is not None)
        span.set_attribute("error_count", len(all_errors))

    return result
