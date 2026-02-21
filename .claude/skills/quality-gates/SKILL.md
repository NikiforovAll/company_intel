---
name: quality-gates
description: This skill should be used when the user wants to run code quality checks (linting, formatting, type checking, tests) on the company_intel project. Use this skill when asked to "run quality gates", "check the code", "run tests", "lint the code", or verify code quality before committing.
---

# Quality Gates

Run code quality checks for the company_intel project.

## Quality Checks

| Check | Command | Directory | Purpose |
|-------|---------|-----------|---------|
| **Ruff Lint** | `uv run ruff check agent main.py --fix` | `src/agent/` | Lint + auto-fix |
| **Ruff Format** | `uv run ruff format agent main.py` | `src/agent/` | Format code |
| **Mypy** | `uv run mypy agent main.py` | `src/agent/` | Static type checking |
| **Aspire Tests** | `dotnet test tests/AppHost.Tests` | repo root | Integration tests |

## Usage

Run default gates (lint + format + mypy):

```bash
.claude/skills/quality-gates/scripts/check.sh
```

Include Aspire integration tests (optional, slower):

```bash
.claude/skills/quality-gates/scripts/check.sh --all
```

Individual checks: `--lint`, `--format`, `--mypy`, `--test`, `--all`

## Workflow

1. Run the check script from the project root
2. Review any failures and fix issues
3. Re-run until all checks pass
4. Present user with concise summary
