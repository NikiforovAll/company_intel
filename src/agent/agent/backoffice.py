from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import logfire
from pydantic_ai import Agent, RunContext

from agent.chunker import chunk_documents
from agent.embedder import get_embedder
from agent.scraper import scrape_company
from agent.scraper.models import ScrapeResult
from agent.scraper.storage import list_companies, load_raw_documents, wipe_raw_data
from agent.settings import get_settings
from agent.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

# prevent background tasks from being garbage collected
_background_tasks: set[asyncio.Task[None]] = set()


@dataclass
class ScrapeJob:
    company: str
    status: str  # "running", "done", "failed"
    started_at: datetime
    finished_at: datetime | None = None
    result: ScrapeResult | None = None
    error: str | None = None
    errors: list[str] = field(default_factory=list)


# in-memory job registry — survives across requests, lost on restart
_scrape_jobs: dict[str, ScrapeJob] = {}

BACKOFFICE_INSTRUCTIONS = """\
You are the Company Intel Backoffice operator. You manage data gathering operations.

RULES:
1. ALWAYS call a tool to perform operations. NEVER answer from memory or guess results.
2. If the company name is ambiguous or misspelled, ask the user to confirm before
   proceeding. E.g., "Did you mean **Figma** or **Fig**?"
3. For destructive operations (delete, re-gather), always confirm with the user first.
4. Report the tool result to the user.
5. If an operation fails, report the error clearly.
6. Be concise and factual.
7. Gathering runs in the background. The tool returns immediately.
   Use check_scrape_status to monitor progress and see errors.
8. You can assume company name if it can be inferred from the context

FORMAT:
- State what action was performed and the result.
- For list operations, use a numbered list.
"""


async def _ingest_to_vectorstore(company: str, data_dir: Path) -> int:
    with logfire.span("ingest_to_vectorstore {company}", company=company):
        store = get_vectorstore()
        store.delete_company(company)

        docs = load_raw_documents(company, data_dir)
        if not docs:
            logger.warning("No raw documents to ingest for '%s'", company)
            return 0

        chunks = chunk_documents(docs)
        if not chunks:
            logger.warning("No chunks produced for '%s'", company)
            return 0

        embedder = get_embedder()
        texts = [c.text for c in chunks]
        dense, sparse = await embedder.embed_texts(texts)

        total = store.upsert_chunks(chunks, dense, sparse)
        logger.info(
            "Ingested %d chunks for '%s' (%d docs)",
            total,
            company,
            len(docs),
        )
        return total


async def _run_scrape(company: str, data_dir: object) -> None:
    job = _scrape_jobs[company]
    with logfire.span("background_scrape {company}", company=company) as span:
        try:
            result = await scrape_company(company, Path(str(data_dir)))
            job.result = result
            job.errors = result.errors

            span.set_attribute("total_documents", result.total_documents)
            span.set_attribute("error_count", len(result.errors))

            logger.info(
                "Background scrape done for '%s': %d docs"
                " (%d website, %d search, wiki=%s, %d errors)",
                company,
                result.total_documents,
                result.website_pages,
                result.search_pages,
                result.wikipedia_scraped,
                len(result.errors),
            )

            await _ingest_to_vectorstore(company, Path(str(data_dir)))

            job.status = "done"
            job.finished_at = datetime.now(UTC)
        except Exception as exc:
            job.status = "failed"
            job.finished_at = datetime.now(UTC)
            job.error = str(exc)

            span.record_exception(exc)
            logger.exception("Background scrape failed for '%s'", company)
            raise


def create_backoffice_agent() -> Agent[None, str]:
    settings = get_settings()
    logger.info("Backoffice agent created", extra={"model": settings.model})

    agent: Agent[None, str] = Agent(
        model=settings.model,
        instructions=BACKOFFICE_INSTRUCTIONS,
    )

    @agent.tool
    async def gather_company_data(
        ctx: RunContext[None],  # noqa: ARG001
        company_name: str,
    ) -> str:
        """Trigger data gathering for a company.

        Launches scraping in the background and returns immediately.
        Use check_scrape_status to monitor progress.

        Args:
            ctx: The run context.
            company_name: The company name to gather data for.
        """
        normalized = company_name.strip().lower()
        logger.info(
            "gather_company_data called",
            extra={"company": normalized},
        )

        existing = _scrape_jobs.get(normalized)
        if existing and existing.status == "running":
            return (
                f"Gathering for '{company_name}' is already in progress "
                f"(started {existing.started_at.isoformat()})."
            )

        _scrape_jobs[normalized] = ScrapeJob(
            company=normalized,
            status="running",
            started_at=datetime.now(UTC),
        )

        task = asyncio.create_task(_run_scrape(normalized, settings.data_dir))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        return (
            f"Gathering started for '{company_name}'. "
            "Scraping is running in the background — "
            "use check_scrape_status to monitor progress."
        )

    @agent.tool
    async def check_scrape_status(
        ctx: RunContext[None],  # noqa: ARG001
        company_name: str,
    ) -> dict[str, object]:
        """Check the status of a scraping job for a company.

        Returns status (running/done/failed), timing, document counts,
        and any errors.

        Args:
            ctx: The run context.
            company_name: The company name to check.
        """
        normalized = company_name.strip().lower()
        job = _scrape_jobs.get(normalized)
        if job is None:
            return {"status": "not_found", "company": normalized}

        info: dict[str, object] = {
            "company": job.company,
            "status": job.status,
            "started_at": job.started_at.isoformat(),
        }
        if job.finished_at:
            info["finished_at"] = job.finished_at.isoformat()
        if job.result:
            info["total_documents"] = job.result.total_documents
            info["website_pages"] = job.result.website_pages
            info["search_pages"] = job.result.search_pages
            info["wikipedia_scraped"] = job.result.wikipedia_scraped
        if job.error:
            info["error"] = job.error
        if job.errors:
            info["scrape_errors"] = job.errors
        return info

    @agent.tool
    async def list_gathered_companies(
        ctx: RunContext[None],  # noqa: ARG001
    ) -> list[dict[str, str | int]]:
        """List all companies that have been gathered into the knowledge base.

        Args:
            ctx: The run context.
        """
        logger.info("list_gathered_companies called")
        return list_companies(settings.data_dir)

    @agent.tool
    async def delete_company_data(
        ctx: RunContext[None],  # noqa: ARG001
        company_name: str,
    ) -> str:
        """Delete all gathered data for a company from the knowledge base.

        Args:
            ctx: The run context.
            company_name: The company name to delete data for.
        """
        normalized = company_name.strip().lower()
        logger.info("delete_company_data called", extra={"company": normalized})

        store = get_vectorstore()
        deleted_points = store.delete_company(normalized)

        raw_dir = settings.data_dir / normalized / "raw"
        if raw_dir.exists():
            wipe_raw_data(normalized, settings.data_dir)
            _scrape_jobs.pop(normalized, None)
            return (
                f"Deleted all data for '{company_name}' "
                f"({deleted_points} vectors removed)."
            )
        if deleted_points > 0:
            return (
                f"Deleted {deleted_points} vectors for '{company_name}' "
                "(no raw files found)."
            )
        return f"No data found for '{company_name}'."

    return agent
