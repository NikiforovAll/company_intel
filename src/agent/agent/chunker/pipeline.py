from __future__ import annotations

import hashlib
import re
import uuid

import tiktoken

from agent.chunker.config import (
    HARD_MAX_TOKENS,
    MIN_CHUNK_TOKENS,
    OVERLAP_TOKENS,
    TARGET_CHUNK_TOKENS,
    TIKTOKEN_ENCODING,
)
from agent.chunker.models import Chunk, ChunkMetadata
from agent.scraper.models import RawDocument

_HEADING_RE = re.compile(r"^#{1,3}\s+", re.MULTILINE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

_enc = tiktoken.get_encoding(TIKTOKEN_ENCODING)


def _token_count(text: str) -> int:
    return len(_enc.encode(text))


def _split_by_headings(text: str) -> list[str]:
    parts = _HEADING_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _split_by_paragraphs(text: str) -> list[str]:
    parts = text.split("\n\n")
    return [p.strip() for p in parts if p.strip()]


def _split_by_sentences(text: str) -> list[str]:
    parts = _SENTENCE_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _split_piece(text: str) -> list[str]:
    """Recursively split text into pieces that fit under HARD_MAX_TOKENS."""
    if _token_count(text) <= HARD_MAX_TOKENS:
        return [text]

    paragraphs = _split_by_paragraphs(text)
    if len(paragraphs) > 1:
        result: list[str] = []
        for p in paragraphs:
            result.extend(_split_piece(p))
        return result

    sentences = _split_by_sentences(text)
    if len(sentences) > 1:
        result = []
        for s in sentences:
            result.extend(_split_piece(s))
        return result

    # last resort: hard split by tokens
    tokens = _enc.encode(text)
    pieces = []
    for i in range(0, len(tokens), HARD_MAX_TOKENS):
        pieces.append(_enc.decode(tokens[i : i + HARD_MAX_TOKENS]))
    return pieces


def _greedy_merge(pieces: list[str]) -> list[str]:
    """Merge small pieces up to TARGET_CHUNK_TOKENS."""
    if not pieces:
        return []

    merged: list[str] = []
    current = pieces[0]

    for piece in pieces[1:]:
        combined = current + "\n\n" + piece
        if _token_count(combined) <= TARGET_CHUNK_TOKENS:
            current = combined
        else:
            merged.append(current)
            current = piece

    merged.append(current)
    return merged


def _add_overlap(chunks: list[str]) -> list[str]:
    """Add token overlap between adjacent chunks."""
    if len(chunks) <= 1:
        return chunks

    result: list[str] = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tokens = _enc.encode(chunks[i - 1])
        overlap_tokens = prev_tokens[-OVERLAP_TOKENS:]
        overlap_text = _enc.decode(overlap_tokens)
        result.append(overlap_text + "\n" + chunks[i])

    return result


def _chunk_id(url: str, chunk_index: int) -> str:
    key = f"{url}::{chunk_index}"
    h = hashlib.sha256(key.encode()).digest()[:16]
    return str(uuid.UUID(bytes=h))


def chunk_document(doc: RawDocument) -> list[Chunk]:
    sections = _split_by_headings(doc.content)
    if not sections:
        sections = [doc.content]

    pieces: list[str] = []
    for section in sections:
        pieces.extend(_split_piece(section))

    merged = _greedy_merge(pieces)
    merged = [c for c in merged if _token_count(c) >= MIN_CHUNK_TOKENS]
    merged = _add_overlap(merged)

    chunks: list[Chunk] = []
    for i, text in enumerate(merged):
        chunks.append(
            Chunk(
                id=_chunk_id(doc.url, i),
                text=text,
                metadata=ChunkMetadata(
                    url=doc.url,
                    title=doc.title,
                    company=doc.company,
                    source_type=doc.source_type,
                    chunk_index=i,
                    scraped_at=doc.scraped_at,
                ),
            )
        )
    return chunks


def chunk_documents(docs: list[RawDocument]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in docs:
        chunks.extend(chunk_document(doc))
    return chunks
