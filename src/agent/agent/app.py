from __future__ import annotations

import logging
from datetime import UTC, datetime

import logfire
import tiktoken
from pydantic_ai import Agent, RunContext

from agent.embedder.pipeline import get_embedder
from agent.settings import get_settings
from agent.vectorstore.client import get_vectorstore
from agent.vectorstore.config import CONTEXT_BUDGET_TOKENS

logger = logging.getLogger(__name__)

INSTRUCTIONS = """\
You are Company Intelligence — a research assistant for Company Intelligence.
Today's date: {current_date}

CRITICAL: You MUST call search_knowledge_base for EVERY user message. No exceptions. \
Never answer from memory. Never skip the search.

RULES:
1. ALWAYS call search_knowledge_base BEFORE generating any answer — even for greetings \
or follow-ups. This is mandatory and non-negotiable.
2. Pass the user's query directly to search_knowledge_base.
3. Answer ONLY from the retrieved context. Never use prior knowledge or training data.
4. If search results are empty or limited, respond with whatever information you have \
from context, and note that data may be limited. \
Contact administrators to add more data.
5. Be concise and factual. No speculation or hedging.
6. Never refuse to search. Never say "based on our previous conversation" \
without searching.

SEARCH STRATEGY:
- Pass the user's query as-is to the `query` parameter. Do NOT transform it.
- If the query mentions exactly ONE company, pass it as the `company` parameter.
- If the query mentions TWO OR MORE companies, or you are uncertain which \
company is meant, do NOT pass `company` — leave it empty to search all.
- For follow-up questions, resolve pronouns ("it", "they", "that company") \
from conversation history to identify the company name, but keep the query \
unchanged.
- For multi-part questions, call search_knowledge_base multiple times \
— once per sub-topic, using the user's original phrasing.

FORMAT:
- Write a short answer using inline citations as [Title of Article](url).
- Use the EXACT title and url from the search results. Never invent or modify titles.
- DEDUPLICATION: Multiple chunks may share the same url. In the "Sources:" \
section, list each unique url EXACTLY ONCE. Never repeat the same url.

EXAMPLE 1 — single company:
User: Tell me about Stripe.
Call: search_knowledge_base(query="Tell me about Stripe", company="stripe")

EXAMPLE 2 — multiple companies (no company filter):
User: Compare Figma and Canva.
Call: search_knowledge_base(query="Compare Figma and Canva")
"""

_enc = tiktoken.get_encoding("cl100k_base")


def _apply_context_budget(
    results: list[dict[str, str]], budget: int = CONTEXT_BUDGET_TOKENS
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    total = 0
    for r in results:
        tokens = len(_enc.encode(r["text"]))
        if total + tokens > budget:
            break
        total += tokens
        out.append(r)
    return out


def create_agent() -> Agent[None, str]:
    settings = get_settings()
    logger.info("Agent created", extra={"model": settings.model})

    instructions = INSTRUCTIONS.format(
        current_date=datetime.now(UTC).strftime("%Y-%m-%d"),
    )

    agent: Agent[None, str] = Agent(
        model=settings.model,
        instructions=instructions,
    )

    @agent.tool
    async def search_knowledge_base(
        ctx: RunContext[None],  # noqa: ARG001
        query: str,
        company: str | None = None,
    ) -> list[dict[str, str]] | str:
        """Search the knowledge base for Company Intelligence.

        Args:
            ctx: The run context.
            query: Search query describing what information to find.
            company: Optional company name to filter results.
                     If not provided, searches across all companies.
        """
        with logfire.span(
            "search_knowledge_base", query=query, company=company or "all"
        ):
            embedder = get_embedder()
            with logfire.span("embed_query"):
                dense_vec, sparse_vec = await embedder.embed_query(query)

            store = get_vectorstore()
            with logfire.span("qdrant_hybrid_search"):
                results = store.search(dense_vec, sparse_vec, company=company)

            budgeted = _apply_context_budget(results)
            logfire.info(
                "search results: {total} found, {kept} after budget",
                total=len(results),
                kept=len(budgeted),
            )
            if not budgeted:
                return "No results found in the knowledge base."
            return budgeted

    return agent
