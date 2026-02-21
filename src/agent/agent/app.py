from __future__ import annotations

import logging

from pydantic_ai import Agent, RunContext

from agent.settings import get_settings

logger = logging.getLogger(__name__)

INSTRUCTIONS = """\
You are Company Intel — a research assistant for company intelligence.

RULES:
1. ALWAYS call search_knowledge_base before answering.
2. Answer ONLY from the retrieved context. Never use prior knowledge.
3. If no relevant context is found, say: "I don't have enough information about that."
4. Be concise and factual. No speculation.

SEARCH STRATEGY:
- Reformulate vague questions into keyword-rich queries with domain terminology.
- For follow-up questions, resolve pronouns ("it", "they", "that company") from
  conversation history into a self-contained search query.
- For multi-part questions, call search_knowledge_base multiple times \
— once per sub-topic.

FORMAT:
- Write a short answer using inline citations as [title](url).
- End with a "Sources:" section listing all referenced sources.

EXAMPLE:
User: Tell me about Stripe.

Stripe is a financial technology company founded in 2010 by Patrick and John Collison \
[About Stripe](https://stripe.com/about). It provides payment processing APIs used by \
millions of businesses [About Stripe](https://stripe.com/about). \
Stripe has raised over \
$8.7 billion in total funding with a $50 billion valuation as of March 2023 \
[Stripe - Crunchbase](https://www.crunchbase.com/organization/stripe).

Sources:
- [About Stripe](https://stripe.com/about)
- [Stripe - Crunchbase](https://www.crunchbase.com/organization/stripe)
"""

MOCK_CHUNKS: list[dict[str, str]] = [
    {
        "url": "https://www.figma.com/about",
        "title": "About Figma",
        "company": "figma",
        "source_type": "website",
        "text": (
            "Figma is a collaborative interface design tool founded in 2012 "
            "by Dylan Field and Evan Wallace. It runs in the browser and "
            "enables real-time collaboration on UI/UX design projects."
        ),
    },
    {
        "url": "https://en.wikipedia.org/wiki/Figma",
        "title": "Figma - Wikipedia",
        "company": "figma",
        "source_type": "wikipedia",
        "text": (
            "In September 2022, Adobe announced plans to acquire Figma for "
            "approximately $20 billion. The deal was abandoned in December 2023 "
            "due to regulatory concerns in the EU and UK."
        ),
    },
    {
        "url": "https://www.figma.com/about",
        "title": "About Figma — Competitors",
        "company": "figma",
        "source_type": "website",
        "text": (
            "Figma's main competitors include Sketch, Adobe XD, and InVision. "
            "Figma differentiates through browser-based real-time collaboration "
            "and a generous free tier for individual users."
        ),
    },
    {
        "url": "https://en.wikipedia.org/wiki/Spotify",
        "title": "Spotify - Wikipedia",
        "company": "spotify",
        "source_type": "wikipedia",
        "text": (
            "Spotify is a Swedish audio streaming service founded in 2006 by "
            "Daniel Ek and Martin Lorentzon. It offers freemium and premium "
            "subscription tiers with over 600 million monthly active users."
        ),
    },
    {
        "url": "https://newsroom.spotify.com/2024-revenue",
        "title": "Spotify Revenue Report 2024",
        "company": "spotify",
        "source_type": "news",
        "text": (
            "Spotify reported annual revenue of EUR 13.2 billion in 2024, "
            "with premium subscribers reaching 230 million. The company "
            "achieved its first full-year operating profit."
        ),
    },
    {
        "url": "https://stripe.com/about",
        "title": "About Stripe",
        "company": "stripe",
        "source_type": "website",
        "text": (
            "Stripe is a financial technology company founded in 2010 by "
            "Patrick and John Collison. It provides payment processing APIs "
            "used by millions of businesses worldwide."
        ),
    },
    {
        "url": "https://www.crunchbase.com/organization/stripe",
        "title": "Stripe - Crunchbase",
        "company": "stripe",
        "source_type": "crunchbase",
        "text": (
            "Stripe has raised over $8.7 billion in total funding. Its last "
            "valuation was $50 billion as of March 2023. Key investors include "
            "Sequoia Capital, Andreessen Horowitz, and Tiger Global."
        ),
    },
    {
        "url": "https://en.wikipedia.org/wiki/Stripe_(company)",
        "title": "Stripe - Wikipedia",
        "company": "stripe",
        "source_type": "wikipedia",
        "text": (
            "Stripe processes hundreds of billions of dollars annually. "
            "Its main competitors are Adyen, Square (Block), and PayPal's "
            "Braintree. Stripe is headquartered in San Francisco and Dublin."
        ),
    },
]


def _search_mock(query: str, company: str | None) -> list[dict[str, str]]:  # noqa: ARG001
    if company:
        normalized = company.strip().lower()
        return [c for c in MOCK_CHUNKS if c["company"] == normalized]
    return MOCK_CHUNKS


def create_agent() -> Agent[None, str]:
    settings = get_settings()
    logger.info("Agent created", extra={"model": settings.model})

    agent: Agent[None, str] = Agent(
        model=settings.model,
        instructions=INSTRUCTIONS,
    )

    @agent.tool
    async def search_knowledge_base(
        ctx: RunContext[None],  # noqa: ARG001
        query: str,
        company: str | None = None,
    ) -> list[dict[str, str]]:
        """Search the knowledge base for company intelligence.

        Args:
            ctx: The run context.
            query: Search query describing what information to find.
            company: Optional company name to filter results.
                     If not provided, searches across all companies.
        """
        logger.info(
            "search_knowledge_base called",
            extra={"query": query, "company": company},
        )
        return _search_mock(query, company)

    return agent
