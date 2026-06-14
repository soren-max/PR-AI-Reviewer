#!/usr/bin/env bash
# =============================================================================
# AI PR Review — Run all tests
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🧪 Running all tests..."
echo ""

# ---------------------------------------------------------------------------
# Backend tests
# ---------------------------------------------------------------------------
echo "=== Backend Tests ==="
cd "$PROJECT_DIR/backend"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python -m pytest tests/ -v --cov=app --cov-report=term-missing "$@"

cd "$PROJECT_DIR"

echo ""
echo "✅ All tests passed!"
