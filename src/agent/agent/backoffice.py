from __future__ import annotations

import logging

from pydantic_ai import Agent, RunContext

from agent.settings import get_settings

logger = logging.getLogger(__name__)

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

FORMAT:
- State what action was performed and the result.
- For list operations, use a numbered list.
"""

MOCK_COMPANIES: dict[str, dict[str, int]] = {
    "figma": {"sources": 3, "chunks": 142},
    "spotify": {"sources": 2, "chunks": 98},
    "stripe": {"sources": 3, "chunks": 156},
}


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
        """Trigger data gathering for a company. Scrapes, chunks, and embeds data.

        Args:
            ctx: The run context.
            company_name: The company name to gather data for.
        """
        normalized = company_name.strip().lower()
        logger.info("gather_company_data called", extra={"company": normalized})
        MOCK_COMPANIES[normalized] = {"sources": 3, "chunks": 150}
        return f"Gathering triggered for '{company_name}'. Pipeline started."

    @agent.tool
    async def list_gathered_companies(
        ctx: RunContext[None],  # noqa: ARG001
    ) -> list[dict[str, str | int]]:
        """List all companies that have been gathered into the knowledge base.

        Args:
            ctx: The run context.
        """
        logger.info("list_gathered_companies called")
        return [{"company": name, **stats} for name, stats in MOCK_COMPANIES.items()]

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
        if normalized in MOCK_COMPANIES:
            del MOCK_COMPANIES[normalized]
            return f"Deleted all data for '{company_name}'."
        return f"No data found for '{company_name}'."

    return agent
