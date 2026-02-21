from __future__ import annotations

import logging

from pydantic_ai import Agent

from agent.settings import get_settings

logger = logging.getLogger(__name__)

INSTRUCTIONS = (
    "You are Company Intel — a research assistant for company intelligence. "
    "Answer concisely."
)


def create_agent() -> Agent[None, str]:
    settings = get_settings()
    logger.info(
        "Agent created",
        extra={"model": settings.model},
    )
    return Agent(model=settings.model, instructions=INSTRUCTIONS)
