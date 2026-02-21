from __future__ import annotations

import logging

from pydantic_ai import Agent

from agent.settings import get_settings

logger = logging.getLogger(__name__)

BACKOFFICE_INSTRUCTIONS = (
    "You are the Company Intel Backoffice operator. "
    "You manage data gathering operations: "
    "trigger gather, re-gather, delete company data, and list gathered companies. "
    "Answer concisely."
)


def create_backoffice_agent() -> Agent[None, str]:
    settings = get_settings()
    logger.info(
        "Backoffice agent created",
        extra={"model": settings.model},
    )
    return Agent(model=settings.model, instructions=BACKOFFICE_INSTRUCTIONS)
