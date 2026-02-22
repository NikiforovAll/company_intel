from __future__ import annotations

from pydantic import BaseModel


class IngestionResult(BaseModel):
    company: str
    documents_loaded: int
    chunks_produced: int
    vectors_stored: int
