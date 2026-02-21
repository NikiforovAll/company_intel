from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from agent.scraper.models import RawDocument

logger = logging.getLogger(__name__)


def _raw_dir(company: str, base_dir: Path) -> Path:
    return base_dir / company / "raw"


def wipe_raw_data(company: str, base_dir: Path) -> None:
    target = _raw_dir(company, base_dir)
    if target.exists():
        shutil.rmtree(target)
        logger.info("Wiped raw data at %s", target)


def save_raw_documents(
    company: str, documents: list[RawDocument], base_dir: Path
) -> int:
    target = _raw_dir(company, base_dir)
    target.mkdir(parents=True, exist_ok=True)

    counters: dict[str, int] = {"website": 0, "search": 0}
    count = 0

    for doc in documents:
        if doc.source_type == "wikipedia":
            filename = "wikipedia.md"
        else:
            counters[doc.source_type] = counters.get(doc.source_type, 0) + 1
            idx = counters[doc.source_type]
            filename = f"{doc.source_type}_{idx:03d}.md"

        frontmatter = (
            f"---\n"
            f"url: {doc.url}\n"
            f"title: {doc.title}\n"
            f"source_type: {doc.source_type}\n"
            f"company: {doc.company}\n"
            f"scraped_at: {doc.scraped_at.isoformat()}\n"
            f"---\n\n"
        )

        path = target / filename
        path.write_text(frontmatter + doc.content, encoding="utf-8")
        count += 1

    logger.info("Saved %d documents to %s", count, target)
    return count


def load_raw_documents(company: str, base_dir: Path) -> list[RawDocument]:
    raw = _raw_dir(company, base_dir)
    if not raw.exists():
        return []

    docs: list[RawDocument] = []
    for path in sorted(raw.glob("*.md")):
        text = path.read_text(encoding="utf-8")

        if not text.startswith("---"):
            continue

        end = text.find("---", 3)
        if end == -1:
            continue

        frontmatter_str = text[3:end].strip()
        body = text[end + 3 :].strip()

        meta: dict[str, str] = {}
        for line in frontmatter_str.splitlines():
            if ": " in line:
                key, val = line.split(": ", 1)
                meta[key.strip()] = val.strip()

        scraped_at_str = meta.get("scraped_at", "")
        try:
            scraped_at = datetime.fromisoformat(scraped_at_str)
        except ValueError:
            scraped_at = datetime.now(UTC)

        source_type = meta.get("source_type", "website")
        if source_type not in ("website", "wikipedia", "search"):
            source_type = "website"

        docs.append(
            RawDocument(
                url=meta.get("url", ""),
                title=meta.get("title", ""),
                content=body,
                source_type=source_type,  # type: ignore[arg-type]
                company=meta.get("company", company),
                scraped_at=scraped_at,
            )
        )

    logger.info("Loaded %d raw documents for '%s'", len(docs), company)
    return docs


def list_companies(base_dir: Path) -> list[dict[str, str | int]]:
    if not base_dir.exists():
        return []

    result: list[dict[str, str | int]] = []
    for entry in sorted(base_dir.iterdir()):
        raw = entry / "raw"
        if raw.is_dir():
            files = list(raw.glob("*.md"))
            result.append({"company": entry.name, "files": len(files)})

    return result
