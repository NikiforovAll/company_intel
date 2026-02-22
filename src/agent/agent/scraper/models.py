from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SourceType = Literal["website", "wikipedia", "search"]


class RawDocument(BaseModel):
    url: str
    title: str
    content: str
    source_type: SourceType
    company: str
    scraped_at: datetime


class ScrapeResult(BaseModel):
    company: str
    website_pages: int
    search_pages: int
    wikipedia_scraped: bool
    wikipedia_pages: int = 0
    total_documents: int
    errors: list[str]


@dataclass
class WikipediaResult:
    document: RawDocument | None
    official_website: str | None
    related_documents: list[RawDocument] = field(default_factory=list)


@dataclass
class SearchResults:
    homepage_url: str | None
    company_urls: list[str] = field(default_factory=list)
    extra_urls: list[str] = field(default_factory=list)
