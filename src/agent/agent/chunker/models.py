from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    url: str
    title: str
    company: str
    source_type: str
    chunk_index: int
    scraped_at: datetime


class Chunk(BaseModel):
    id: str
    text: str
    metadata: ChunkMetadata
