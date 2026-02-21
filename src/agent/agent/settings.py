from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(slots=True)
class Settings:
    model: str
    ollama_base_url: str
    data_dir: Path
    qdrant_endpoint: str
    qdrant_api_key: str | None
    embed_model: str
    embed_base_url: str


def _parse_connection_string(conn_str: str) -> dict[str, str]:
    return dict(part.split("=", 1) for part in conn_str.split(";") if "=" in part)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # LLM model
    llm_conn = os.environ.get("ConnectionStrings__ollama-qwen3", "")  # noqa: SIM112
    if not llm_conn:
        raise RuntimeError("ConnectionStrings__ollama-qwen3 is not set")

    llm_parts = _parse_connection_string(llm_conn)
    llm_endpoint = llm_parts["Endpoint"].rstrip("/")
    model_name = llm_parts["Model"]

    base_url = llm_endpoint if llm_endpoint.endswith("/v1") else f"{llm_endpoint}/v1"
    os.environ.setdefault("OLLAMA_BASE_URL", base_url)

    # Embedding model
    embed_conn = os.environ.get(
        "ConnectionStrings__ollama-snowflake-arctic-embed",  # noqa: SIM112
        "",
    )
    if not embed_conn:
        raise RuntimeError(
            "ConnectionStrings__ollama-snowflake-arctic-embed is not set"
        )

    embed_parts = _parse_connection_string(embed_conn)
    embed_base_url = embed_parts["Endpoint"].rstrip("/")
    embed_model = embed_parts["Model"]

    # Qdrant — prefer HTTP endpoint over gRPC
    qdrant_conn = os.environ.get(
        "ConnectionStrings__qdrant_http",  # noqa: SIM112
        os.environ.get("ConnectionStrings__qdrant", ""),  # noqa: SIM112
    )
    if not qdrant_conn:
        raise RuntimeError(
            "ConnectionStrings__qdrant_http or ConnectionStrings__qdrant is not set"
        )

    qdrant_parts = _parse_connection_string(qdrant_conn)
    qdrant_endpoint = qdrant_parts["Endpoint"]
    qdrant_api_key = qdrant_parts.get("Key") or None

    # agent/settings.py -> agent/ -> src/agent/ -> src/ -> repo root
    _repo_root = Path(__file__).resolve().parents[3]
    data_dir = Path(os.environ.get("DATA_DIR", str(_repo_root / "artifacts" / "data")))

    return Settings(
        model=f"ollama:{model_name}",
        ollama_base_url=base_url,
        data_dir=data_dir,
        qdrant_endpoint=qdrant_endpoint,
        qdrant_api_key=qdrant_api_key,
        embed_model=embed_model,
        embed_base_url=embed_base_url,
    )
