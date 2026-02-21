# Tradeoff: Web Scraping

## Decision: Crawl4AI

## Alternatives Considered

| Option                   | Type          | Cost    | Markdown Output   | JS Rendering     | Async |
| ------------------------ | ------------- | ------- | ----------------- | ---------------- | ----- |
| **Crawl4AI**             | OSS library   | Free    | Native            | Yes (Playwright) | Yes   |
| Firecrawl                | Cloud API     | $29+/mo | Yes               | Yes              | Yes   |
| BeautifulSoup + requests | OSS library   | Free    | Manual conversion | No               | No    |
| Scrapy                   | OSS framework | Free    | Manual conversion | Via plugin       | Yes   |
| Playwright direct        | OSS library   | Free    | Manual conversion | Yes              | Yes   |

## Tradeoffs

### Crawl4AI (chosen)

**Pros:**
- Purpose-built for LLM pipelines — outputs clean Markdown by default
- Async, handles JS-rendered pages via Playwright
- Built-in boilerplate removal (nav, footer, ads)
- Free, open-source, actively maintained
- Configurable extraction strategies (CSS, LLM-based, cosine)

**Cons:**
- Playwright dependency adds ~500MB RAM + browser binary
- Less mature than Scrapy for large-scale crawling
- Limited community compared to BeautifulSoup/Scrapy
- Playwright startup time (~2-3s cold start)

### Firecrawl (rejected)

**Pros:** Excellent quality, managed infrastructure, handles edge cases well
**Cons:** Paid, cloud-dependent — violates offline-first principle for gather phase. Adds external dependency for a POC.

### BeautifulSoup + requests (rejected)

**Pros:** Minimal dependencies, well-known, lightweight
**Cons:** No JS rendering — misses SPAs and dynamically loaded content. Manual HTML→Markdown conversion needed. Synchronous.

### Scrapy (rejected)

**Pros:** Battle-tested for large-scale crawling, middleware ecosystem, built-in rate limiting
**Cons:** Overkill for ~20 pages per company. Framework-heavy. No native Markdown output. Steeper learning curve for simple use cases.

## Key Decision Factors

1. **Markdown output is critical** — embedding quality depends on clean text, not raw HTML
2. **JS rendering needed** — many company sites are SPAs (React, Next.js)
3. **POC scope is small** — we scrape ~20 pages per company, not thousands
4. **Offline gather is acceptable** — internet needed only during scrape, not query

## Risks

- Crawl4AI quality on complex sites (heavy JS, iframes) — mitigate: fallback to raw HTML + manual cleaning
- Playwright memory on resource-constrained machines — mitigate: reuse browser instance across pages
- Rate limiting / IP blocking — mitigate: respect robots.txt, 1 req/s, randomize user-agent
