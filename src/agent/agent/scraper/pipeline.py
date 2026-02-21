from __future__ import annotations

import logging
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
from agent.scraper.models import RawDocument, ScrapeResult
from agent.scraper.storage import save_raw_documents, wipe_raw_data

logger = logging.getLogger(__name__)


def _normalize_company(name: str) -> str:
    return name.strip().lower()


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

        # 1. Wikipedia — also extracts official website URL
        wiki_result = await scrape_wikipedia(company)
        if wiki_result.document:
            all_docs.append(wiki_result.document)
            seen_urls.add(wiki_result.document.url)

        # 2. DuckDuckGo search — classify by company domain
        search_results = search_company(
            company, known_homepage=wiki_result.official_website
        )

        # 3. Resolve homepage URL (Wikipedia infobox > DDG first result)
        homepage_url = wiki_result.official_website or search_results.homepage_url
        span.set_attribute("homepage_url", homepage_url or "")

        # 4. Website deep crawl (homepage BFS)
        website_docs: list[RawDocument] = []
        if homepage_url:
            website_docs, website_errors = await scrape_website(homepage_url, company)
            all_docs.extend(website_docs)
            all_errors.extend(website_errors)
            seen_urls.update(d.url for d in website_docs)
        else:
            logger.warning("No homepage URL found for %s", company)

        # 4b. Probe common subdomains (newsroom, about, investors, ...)
        if homepage_url:
            probed = await probe_company_subdomains(homepage_url)
            for u in probed:
                if u not in seen_urls and u not in search_results.company_urls:
                    search_results.company_urls.append(u)

        # 5. Company pages — shallow BFS (about, newsroom, blog)
        co_urls = [u for u in search_results.company_urls if u not in seen_urls]
        if co_urls:
            co_docs, co_errors = await scrape_company_pages(co_urls, company, seen_urls)
            all_docs.extend(co_docs)
            all_errors.extend(co_errors)

        # 6. Third-party content (news, blogs, analyses)
        extra_urls = [u for u in search_results.extra_urls if u not in seen_urls]
        search_docs, search_errors = await scrape_search_results(extra_urls, company)
        all_docs.extend(search_docs)
        all_errors.extend(search_errors)

        saved = save_raw_documents(company, all_docs, data_dir)

        result = ScrapeResult(
            company=company,
            website_pages=len(website_docs),
            search_pages=len(search_docs),
            wikipedia_scraped=wiki_result.document is not None,
            total_documents=saved,
            errors=all_errors,
        )

        span.set_attribute("total_documents", saved)
        span.set_attribute("website_pages", len(website_docs))
        span.set_attribute("search_pages", len(search_docs))
        span.set_attribute("wikipedia_scraped", wiki_result.document is not None)
        span.set_attribute("error_count", len(all_errors))

    return result
