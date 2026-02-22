from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import logfire
from fastapi import APIRouter
from pydantic import BaseModel

from agent.embedder.pipeline import get_embedder
from agent.ingestion import ingest_company
from agent.settings import get_settings
from agent.vectorstore.client import get_vectorstore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/eval", tags=["eval"])

_background_tasks: set[asyncio.Task[None]] = set()


@dataclass
class EvalJob:
    run_id: str
    company: str
    status: str  # "running", "completed", "failed"
    phase: str  # "ingesting", "searching", "evaluating", "done"
    progress: str
    started_at: datetime
    finished_at: datetime | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    per_query: list[dict] = field(default_factory=list)
    ingestion: dict | None = None
    error: str | None = None


_eval_jobs: dict[str, EvalJob] = {}


# --- Models ---


class IngestRequest(BaseModel):
    company: str


class IngestResponse(BaseModel):
    company: str
    documents_loaded: int
    chunks_produced: int
    vectors_stored: int


class SearchRequest(BaseModel):
    query: str
    company: str | None = None
    limit: int = 10


class SearchResult(BaseModel):
    url: str
    title: str
    company: str
    source_type: str
    text: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


class RunRequest(BaseModel):
    company: str


class RunResponse(BaseModel):
    run_id: str
    status: str


# --- Endpoints ---


@router.post("/run", response_model=RunResponse, status_code=202)
async def eval_run(req: RunRequest) -> RunResponse:
    """Start eval run in background. Poll /eval/status for results."""
    company = req.company.strip().lower()
    run_id = f"{company}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    existing = _eval_jobs.get(company)
    if existing and existing.status == "running":
        return RunResponse(run_id=existing.run_id, status="already_running")

    job = EvalJob(
        run_id=run_id,
        company=company,
        status="running",
        phase="starting",
        progress="",
        started_at=datetime.now(UTC),
    )
    _eval_jobs[company] = job

    task = asyncio.create_task(_run_eval(job))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return RunResponse(run_id=run_id, status="started")


@router.get("/status")
async def eval_status(run_id: str) -> dict:
    """Check status of an eval run."""
    for job in _eval_jobs.values():
        if job.run_id == run_id:
            result: dict = {
                "run_id": job.run_id,
                "status": job.status,
                "phase": job.phase,
                "progress": job.progress,
            }
            if job.finished_at:
                result["finished_at"] = job.finished_at.isoformat()
            if job.metrics:
                result["metrics"] = job.metrics
            if job.error:
                result["error"] = job.error
            return result
    return {"run_id": run_id, "status": "not_found"}


# --- Background eval logic ---


def _golden_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "tests" / "golden"


def _load_golden(company: str) -> dict:
    """Load golden dataset from tests/golden/{company}.json"""
    golden_path = _golden_dir() / f"{company}.json"
    with open(golden_path) as f:
        return json.load(f)  # type: ignore[no-any-return]


def _setup_eval_logger(run_id: str) -> logging.Logger:
    """Create a file logger for this eval run."""
    report_dir = get_settings().data_dir.parent / "eval"
    report_dir.mkdir(parents=True, exist_ok=True)
    log_path = report_dir / f"{run_id}.log"

    eval_logger = logging.getLogger(f"eval.{run_id}")
    eval_logger.setLevel(logging.INFO)

    class FlushHandler(logging.FileHandler):
        def emit(self, record: logging.LogRecord) -> None:
            super().emit(record)
            self.flush()

    handler = FlushHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    )
    eval_logger.addHandler(handler)
    return eval_logger


async def _run_eval(job: EvalJob) -> None:
    with logfire.span("eval_run {company}", company=job.company):
        try:
            log = _setup_eval_logger(job.run_id)
            golden = _load_golden(job.company)
            queries = golden["queries"]

            # 1. Ingest from test data next to golden dataset
            job.phase = "ingesting"
            job.progress = "loading and embedding documents"
            log.info("ingesting %s from golden dir", job.company)
            ing_result = await ingest_company(job.company, _golden_dir())
            job.ingestion = ing_result.model_dump()
            log.info(
                "ingested %d docs -> %d chunks -> %d vectors",
                ing_result.documents_loaded,
                ing_result.chunks_produced,
                ing_result.vectors_stored,
            )

            # 2. Search each query
            job.phase = "searching"
            embedder = get_embedder()
            store = get_vectorstore()

            scorable = [q for q in queries if q.get("reference_contexts")]
            total = len(scorable)
            log.info(
                "searching %d queries (skipped %d without reference_contexts)",
                total,
                len(queries) - total,
            )

            per_query_results: list[dict] = []
            hit_count = 0
            recall_scores: list[float] = []

            for i, q in enumerate(scorable):
                job.progress = f"{i + 1}/{total} queries"
                log.info("[%d/%d] q=%s: %s", i + 1, total, q["id"], q["query"])

                dense, sparse = await embedder.embed_query(q["query"])
                results = store.search(dense, sparse, company=job.company, limit=5)

                retrieved_texts = [r["text"] for r in results]
                retrieved_urls = [r["url"] for r in results]
                joined = " ".join(t.lower() for t in retrieved_texts)
                log.info("  retrieved %d chunks", len(results))

                # Substring recall: fraction of reference_contexts found in retrieved
                ref_contexts = q["reference_contexts"]
                found = sum(1 for ref in ref_contexts if ref.lower() in joined)
                recall = found / len(ref_contexts) if ref_contexts else 0.0
                hit = recall > 0
                recall_scores.append(recall)
                if hit:
                    hit_count += 1

                log.info("  recall=%.2f hit=%s", recall, hit)

                per_query_results.append(
                    {
                        "id": q["id"],
                        "query": q["query"],
                        "retrieved_urls": retrieved_urls,
                        "retrieved_texts": retrieved_texts,
                        "context_recall": recall,
                        "hit": hit,
                    }
                )

            # 3. Aggregate
            job.phase = "evaluating"
            job.progress = "computing retrieval metrics"
            n = len(scorable) or 1
            metrics = {
                "hit_rate": hit_count / n,
                "context_recall": sum(recall_scores) / n,
                "queries_evaluated": len(scorable),
            }

            log.info(
                "DONE hit_rate=%.2f recall=%.2f (%d queries)",
                metrics["hit_rate"],
                metrics["context_recall"],
                metrics["queries_evaluated"],
            )

            # 5. Write report
            report = {
                "run_id": job.run_id,
                "company": job.company,
                "timestamp": datetime.now(UTC).isoformat(),
                "ingestion": job.ingestion,
                "metrics": metrics,
                "per_query": per_query_results,
            }

            report_dir = get_settings().data_dir.parent / "eval"
            report_dir.mkdir(parents=True, exist_ok=True)
            report_path = report_dir / f"{job.run_id}_report.json"
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2, default=str)

            logfire.info(
                "eval completed for {company}: "
                "hit_rate={hit_rate:.2f} recall={recall:.2f}",
                company=job.company,
                hit_rate=metrics["hit_rate"],
                recall=metrics["context_recall"],
            )

            # 6. Update job
            job.metrics = metrics
            job.per_query = per_query_results
            job.status = "completed"
            job.phase = "done"
            job.finished_at = datetime.now(UTC)

        except Exception as exc:
            job.status = "failed"
            job.phase = "error"
            job.error = str(exc)
            job.finished_at = datetime.now(UTC)
            logger.exception("Eval failed for '%s'", job.company)
