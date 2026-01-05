#!/bin/bash
set -e

echo "🧪 Running Smoke Tests..."

# 1. API Health Check
HEALTH=$(curl -s http://localhost:8100/health)
if [[ $HEALTH == *"online"* ]]; then
    echo "✅ /health: OK ($HEALTH)"
else
    echo "❌ /health: FAILED ($HEALTH)"
    exit 1
fi

echo "✨ All Systems Go"
