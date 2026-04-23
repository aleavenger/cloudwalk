#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v npx >/dev/null 2>&1; then
  echo "[check] Playwright dashboard validation skipped: npx is not installed."
  exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[check] Playwright dashboard validation skipped: npm is not installed."
  exit 0
fi

if ! node -e "require('playwright');" >/dev/null 2>&1; then
  echo "[check] Playwright package not found locally. Attempting temporary install..."
  if ! npm install --no-save playwright >/dev/null 2>&1; then
    echo "[check] Playwright dashboard validation skipped: playwright package is unavailable."
    exit 0
  fi
fi

if ! node -e "const { chromium } = require('playwright'); chromium.launch().then(async (b)=>{await b.close();}).catch(()=>process.exit(1));" >/dev/null 2>&1; then
  if ! npx playwright install chromium >/dev/null 2>&1; then
    echo "[check] Playwright dashboard validation skipped: chromium browser runtime is unavailable."
    exit 0
  fi
fi

GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:${GRAFANA_PORT:-3000}}"
PLAYWRIGHT_OUTPUT_DIR="${PLAYWRIGHT_OUTPUT_DIR:-logs/playwright}"

cd "${ROOT_DIR}"
node scripts/check_grafana_dashboard_playwright.js
