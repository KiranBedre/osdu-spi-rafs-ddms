#!/usr/bin/env bash

set -euo pipefail

RESULTS_DIR="tests/results"
REPORT="$RESULTS_DIR/rafs.xml"
mkdir -p "$RESULTS_DIR"
rm -f "$REPORT"

exec python -m pytest \
  -c tests/integration/pytest.ini \
  -n auto \
  --dist=loadscope \
  tests/integration/tests \
  --junitxml="$REPORT" \
  "$@"
