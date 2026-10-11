#!/usr/bin/env bash

set -euo pipefail
export PYTHONUTF8=1

RESULTS_DIR=".spi/results"
mkdir -p "$RESULTS_DIR"
rm -f "$RESULTS_DIR/test-results.xml" "$RESULTS_DIR/coverage.xml"

base_ref=""
if [[ -n "${GITHUB_BASE_REF:-}" ]] && git rev-parse --verify "origin/$GITHUB_BASE_REF" >/dev/null 2>&1; then
  base_ref="$(git merge-base HEAD "origin/$GITHUB_BASE_REF")"
elif [[ -z "$(git status --porcelain)" ]] && git rev-parse --verify HEAD^ >/dev/null 2>&1; then
  base_ref="HEAD^"
fi

lint_sources=()
mapfile -t lint_sources < <(
  {
    if [[ -n "$base_ref" ]]; then
      git diff --name-only --diff-filter=ACMRT "$base_ref" HEAD -- "*.py"
    fi
    git diff --name-only --diff-filter=ACMRT HEAD -- "*.py"
    git ls-files --others --exclude-standard -- "*.py"
  } | awk '/^(app|client|tests)\/.*\.py$/' | sort -u
)

if (( ${#lint_sources[@]} > 0 )); then
  pre-commit run --files "${lint_sources[@]}"
else
  echo "No changed Python files to lint"
fi

python -m pytest \
  tests/test_api \
  tests/test_helpers \
  tests/test_models \
  tests/test_providers \
  tests/test_validation \
  --junitxml="$RESULTS_DIR/test-results.xml" \
  --cov=app \
  --cov-report="xml:$RESULTS_DIR/coverage.xml"
