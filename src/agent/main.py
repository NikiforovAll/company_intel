from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic_ai.ui.ag_ui import AGUIAdapter
from starlette.requests import Request
from starlette.responses import Response

from agent.app import create_agent
from agent.backoffice import create_backoffice_agent
from agent.telemetry import configure_telemetry

configure_telemetry()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    from agent.embedder import get_embedder

    logger.info("Agent service started")
    get_embedder()
    yield
    logger.info("Agent service shutting down")


app = FastAPI(title="Company Intelligence Agent", lifespan=lifespan)
logfire.instrument_fastapi(app, excluded_urls="/health")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = create_agent()
backoffice_agent = create_backoffice_agent()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/")
async def run_agent(request: Request) -> Response:
    with logfire.span("agent request"):
        try:
            response = await AGUIAdapter.dispatch_request(request, agent=agent)
            logger.info(
                "Agent request completed",
                extra={"status_code": response.status_code},
            )
            return response
        except Exception:
            logger.exception("Agent request failed")
            raise


@app.post("/backoffice")
async def run_backoffice_agent(request: Request) -> Response:
    with logfire.span("backoffice agent request"):
        try:
            response = await AGUIAdapter.dispatch_request(
                request, agent=backoffice_agent
            )
            logger.info(
                "Backoffice agent request completed",
                extra={"status_code": response.status_code},
            )
            return response
        except Exception:
            logger.exception("Backoffice agent request failed")
            raise


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,  # noqa: ARG001
) -> JSONResponse:
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
