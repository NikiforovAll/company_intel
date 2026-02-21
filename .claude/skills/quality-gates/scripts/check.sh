#!/usr/bin/env bash
# Quality Gates - Run code quality checks for company_intel
# Usage: check.sh [--lint] [--format] [--mypy] [--test] [--all]
set -e

cd "$(git rev-parse --show-toplevel)"

RUN_LINT=false
RUN_FORMAT=false
RUN_MYPY=false
RUN_TEST=false

# Default: lint + format + mypy (no tests — use --test or --all)
if [[ $# -eq 0 ]]; then
  RUN_LINT=true
  RUN_FORMAT=true
  RUN_MYPY=true
fi

for arg in "$@"; do
  case $arg in
    --lint)   RUN_LINT=true ;;
    --format) RUN_FORMAT=true ;;
    --mypy)   RUN_MYPY=true ;;
    --test)   RUN_TEST=true ;;
    --all)
      RUN_LINT=true
      RUN_FORMAT=true
      RUN_MYPY=true
      RUN_TEST=true
      ;;
  esac
done

AGENT_DIR="src/agent"

echo "=== Running Quality Gates ==="
echo ""

step=1

if $RUN_LINT; then
  echo "[$step] Ruff Lint (with auto-fix)..."
  uv run --directory "$AGENT_DIR" ruff check agent main.py --fix
  echo "OK"
  echo ""
  ((step++))
fi

if $RUN_FORMAT; then
  echo "[$step] Ruff Format..."
  uv run --directory "$AGENT_DIR" ruff format agent main.py
  echo "OK"
  echo ""
  ((step++))
fi

if $RUN_MYPY; then
  echo "[$step] Mypy Type Check..."
  uv run --directory "$AGENT_DIR" mypy agent main.py
  echo "OK"
  echo ""
  ((step++))
fi

if $RUN_TEST; then
  echo "[$step] Aspire Integration Tests..."
  dotnet test tests/AppHost.Tests -p:WarningLevel=0 --no-restore -q 2>&1
  test_status=$?
  if [[ $test_status -ne 0 ]]; then
    exit "$test_status"
  fi
  echo "OK"
  echo ""
fi

echo "=== All Quality Gates Passed ==="
