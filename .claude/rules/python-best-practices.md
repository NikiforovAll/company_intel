# Python Best Practices

## Dev Setup

- **uv** for all dependency management (`uv sync`, `uv run`, `uv add`)
- **`pyproject.toml`** as single config source for ruff, mypy, pytest — no separate config files
- **`.python-version`** file in repo root for consistent Python version across contributors
- **`uv.lock`** committed to git for reproducible installs
- **Pre-commit hooks** as local system hooks using `uv run` (not pinned remote repos) to avoid version drift:
  ```yaml
  - repo: local
    hooks:
      - id: ruff-check
        entry: uv run ruff check --fix
        language: system
        types: [python]
      - id: ruff-format
        entry: uv run ruff format
        language: system
        types: [python]
      - id: mypy
        entry: uv run mypy src
        language: system
        types: [python]
        pass_filenames: false
  ```

## Code Quality

- **ruff** lint rules: `E, W, F, I, B, C4, UP, ARG, SIM`
- **ruff** as formatter (replaces black/isort)
- **mypy** with `disallow_untyped_defs = true` — all functions must have type hints
- **Modern union syntax**: `X | None` not `Optional[X]`, `list[str]` not `List[str]`

## Idiomatic Python

- **`@dataclass(slots=True)`** on all dataclasses — less memory, faster access, prevents typo bugs
- **Pydantic `BaseModel`** for API request/response contracts and validation boundaries — not for internal data
- **`StrEnum`** for string-valued enums (Python 3.11+):
  ```python
  class TransportType(StrEnum):
      STDIO = "stdio"
      HTTP = "http"
  ```
- **`__all__`** in public modules to make the API explicit
- **`pathlib.Path`** over `os.path` for all path operations
- **f-strings** over `.format()` or `%`
- **Context managers** (`with`) for resource cleanup (files, connections, locks)
- **Structural pattern matching** (`match/case`) when cleaner than if/elif chains
- **`from __future__ import annotations`** for forward references when needed

## CI

- **`pip-audit`** (via `uvx pip-audit`) for dependency vulnerability scanning
- **Gate order**: lint → format check → type check → test → security audit
