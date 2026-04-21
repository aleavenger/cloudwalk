#!/usr/bin/env bash
set -euo pipefail

: "${HOST:=0.0.0.0}"
: "${PORT:=8000}"

mkdir -p /app/database/report /app/charts /app/logs

echo "[bootstrap] Running checkout anomaly analysis..."
python -m scripts.checkout_analysis

echo "[bootstrap] Generating checkout charts..."
python -m scripts.generate_checkout_charts

echo "[startup] Starting FastAPI service on ${HOST}:${PORT}"
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}"
