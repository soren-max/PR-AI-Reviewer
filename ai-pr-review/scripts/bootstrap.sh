#!/usr/bin/env bash
# =============================================================================
# AI PR Review — Bootstrap Script
# =============================================================================
# Sets up the development environment from scratch.
# Usage: ./scripts/bootstrap.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "🚀 Bootstrapping AI PR Review development environment..."
echo ""

# ---------------------------------------------------------------------------
# Check prerequisites
# ---------------------------------------------------------------------------
echo "📋 Checking prerequisites..."

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        echo "❌ $1 is not installed. Please install it first."
        exit 1
    fi
    echo "  ✅ $1 found: $(command -v "$1")"
}

check_cmd python3
check_cmd node
check_cmd npm

echo ""

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
echo "🔧 Setting up backend..."
cd "$PROJECT_DIR/backend"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  ✅ Created virtual environment"
fi

source .venv/bin/activate
pip install -q -r requirements-dev.txt
echo "  ✅ Installed Python dependencies"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  ⚠️  Created .env from .env.example — please edit it with your API keys"
fi

cd "$PROJECT_DIR"
echo ""

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
echo "🔧 Setting up frontend..."
cd "$PROJECT_DIR/frontend"

npm install --silent
echo "  ✅ Installed Node.js dependencies"

if [ ! -f ".env.local" ]; then
    cp .env.local.example .env.local
    echo "  ✅ Created .env.local"
fi

cd "$PROJECT_DIR"
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "✅ Bootstrap complete!"
echo ""
echo "Quick start:"
echo "  make dev          # Start backend + frontend"
echo "  make test         # Run backend tests"
echo "  make lint         # Lint all code"
echo "  make docker-up    # Start via Docker Compose"
echo ""
echo "📁 Project: $PROJECT_DIR"
