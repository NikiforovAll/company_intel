from __future__ import annotations

import logging
from pathlib import Path

import logfire

from agent.chunker import chunk_documents
from agent.embedder import get_embedder
from agent.ingestion.models import IngestionResult
from agent.scraper.storage import load_raw_documents
from agent.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


async def ingest_company(company: str, data_dir: Path) -> IngestionResult:
    """Load raw docs, chunk, embed, and upsert to vector store."""
    with logfire.span("ingest_company {company}", company=company):
        store = get_vectorstore()
        store.delete_company(company)

        docs = load_raw_documents(company, data_dir)
        if not docs:
            logger.warning("No raw documents to ingest for '%s'", company)
            return IngestionResult(
                company=company,
                documents_loaded=0,
                chunks_produced=0,
                vectors_stored=0,
            )

        chunks = chunk_documents(docs)
        if not chunks:
            logger.warning("No chunks produced for '%s'", company)
            return IngestionResult(
                company=company,
                documents_loaded=len(docs),
                chunks_produced=0,
                vectors_stored=0,
            )

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

        return IngestionResult(
            company=company,
            documents_loaded=len(docs),
            chunks_produced=len(chunks),
            vectors_stored=total,
        )
