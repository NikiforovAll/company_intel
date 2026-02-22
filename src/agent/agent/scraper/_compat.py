"""Windows compatibility for Crawl4AI.

Uvicorn uses SelectorEventLoop on Windows, which lacks subprocess support.
Playwright (used by Crawl4AI) needs subprocesses to launch Chromium.
This module runs browser operations in a thread with ProactorEventLoop.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor

from opentelemetry import context as otel_context

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="crawl4ai")


def _run_in_new_loop[T](fn: Callable[[], Awaitable[T]], ctx: otel_context.Context) -> T:
    token = otel_context.attach(ctx)
    try:
        if sys.platform == "win32":
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(fn())
        finally:
            loop.close()
    finally:
        otel_context.detach(token)


async def run_in_crawler_thread[T](fn: Callable[[], Awaitable[T]]) -> T:
    """Run an async callable in a thread with ProactorEventLoop on Windows.

    Propagates OpenTelemetry context to the worker thread.
    """
    ctx = otel_context.get_current()
    return await asyncio.get_running_loop().run_in_executor(
        _pool, _run_in_new_loop, fn, ctx
    )
