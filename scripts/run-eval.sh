#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_PROJECT="$REPO_ROOT/tests/AppHost.Tests"
FILTER="FullyQualifiedName~RetrievalEvalTests"
EVAL_DIR="$REPO_ROOT/artifacts/eval"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$EVAL_DIR/run-$TIMESTAMP.log"

mkdir -p "$EVAL_DIR"

echo "=== RAG Retrieval Quality Evaluation ==="
echo ""

# Build
echo "[1/3] Building test project..."
dotnet build "$TEST_PROJECT" -p:WarningLevel=0 /clp:ErrorsOnly --verbosity minimal > /dev/null 2>&1
echo "  Build OK"
echo ""

# Run test with tee
echo "[2/3] Running eval..."
echo "  Log: $LOG_FILE"
echo ""

dotnet test "$TEST_PROJECT" --no-build \
  --filter "$FILTER" \
  --logger "console;verbosity=detailed" 2>&1 > "$LOG_FILE" || true

echo ""

# Check pass/fail from log
if grep -q "Test Run Successful" "$LOG_FILE"; then
  echo "[3/3] PASSED"
elif grep -q "Test Run Failed" "$LOG_FILE"; then
  echo "[3/3] FAILED"
  echo ""
  grep -E "(Hit Rate|Context Recall) .* <" "$LOG_FILE" | while IFS= read -r line; do
    echo "  $line"
  done
fi

# Find latest report (eval.py writes {run_id}_report.json)
echo ""
REPORT=$(ls -t "$EVAL_DIR"/*_report.json 2>/dev/null | head -1)
if [ -n "$REPORT" ]; then
  echo "=== Report: $REPORT ==="
  echo ""
  jq -r '
    "Run:     \(.run_id)",
    "Company: \(.company)",
    "Time:    \(.timestamp)",
    "",
    "Metrics:",
    "  Hit Rate:       \(.metrics.hit_rate)",
    "  Context Recall: \(.metrics.context_recall)",
    "  Queries:        \(.metrics.queries_evaluated)",
    "",
    "Per Query:",
    (.per_query[] | "  \(.id) recall=\(.context_recall) hit=\(.hit)\t\(.query)")
  ' "$REPORT"
else
  echo "No report file found in $EVAL_DIR"
fi
