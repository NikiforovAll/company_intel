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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    conn_str = os.environ.get("ConnectionStrings__ollama-qwen3", "")  # noqa: SIM112

    endpoint = "http://localhost:11434"
    model_name = "qwen3"

    if conn_str:
        parts = dict(part.split("=", 1) for part in conn_str.split(";") if "=" in part)
        endpoint = parts.get("Endpoint", endpoint)
        model_name = parts.get("Model", model_name)

    base_url = endpoint.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    os.environ.setdefault("OLLAMA_BASE_URL", base_url)

    # agent/settings.py -> agent/ -> src/agent/ -> src/ -> repo root
    _repo_root = Path(__file__).resolve().parents[3]
    data_dir = Path(os.environ.get("DATA_DIR", str(_repo_root / "artifacts" / "data")))

    return Settings(
        model=f"ollama:{model_name}",
        ollama_base_url=base_url,
        data_dir=data_dir,
    )
