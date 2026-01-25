#!/bin/bash
# PHASE 1 PLAYWRIGHT VERIFICATION EXECUTION SCRIPT
# 
# This script handles the complete Phase 1 automation verification
# Usage:
#   ./run_phase1_tests.sh          # Run all tests (headless)
#   ./run_phase1_tests.sh headed   # Run with browser visible
#   ./run_phase1_tests.sh debug    # Run with debugger

set -e  # Exit on error

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

MODE="${1:-headless}"

echo "🚀 PHASE 1 PLAYWRIGHT VERIFICATION"
echo "=================================="
echo "Mode: $MODE"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm install
  echo ""
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
  echo "🐍 Python environment not activated. Activating..."
  
  if [ -d ".venv-1" ]; then
    source .venv-1/bin/activate 2>/dev/null || source .venv-1/Scripts/activate 2>/dev/null
  elif [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
  else
    echo "❌ Virtual environment not found!"
    exit 1
  fi
fi

echo "✅ Environment ready"
echo ""

# Run tests based on mode
case "$MODE" in
  "headless")
    echo "🎬 Running tests in HEADLESS mode..."
    npm test
    ;;
  "headed")
    echo "👀 Running tests in HEADED mode (browser visible)..."
    npm run test:headed
    ;;
  "debug")
    echo "🐛 Running tests in DEBUG mode..."
    npm run test:debug
    ;;
  "owner")
    echo "👤 Running OWNER REGISTRATION tests only..."
    npm run test:owner
    ;;
  "admin")
    echo "👨‍💼 Running ADMIN APPROVAL tests only..."
    npm run test:admin
    ;;
  "visibility")
    echo "👁️ Running USER VISIBILITY tests only..."
    npm run test:visibility
    ;;
  "negative")
    echo "❌ Running NEGATIVE TEST CASES only..."
    npm run test:negative
    ;;
  *)
    echo "❌ Unknown mode: $MODE"
    echo "Usage: ./run_phase1_tests.sh [headless|headed|debug|owner|admin|visibility|negative]"
    exit 1
    ;;
esac

echo ""
echo "=================================="
echo "✅ TESTS COMPLETE"
echo ""
echo "📊 View detailed report:"
echo "   npm run test:report"
echo ""
echo "📄 Test results:"
echo "   - HTML: playwright-report/index.html"
echo "   - JSON: test-results.json"
echo "   - XML: test-results.xml"
echo ""
