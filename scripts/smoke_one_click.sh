#!/usr/bin/env bash
set -euo pipefail

API_PORT="${API_PORT:-8000}"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"
API_KEY="${MONITORING_API_KEY:-reviewer-local-demo-key}"

API_URL="http://127.0.0.1:${API_PORT}"
GRAFANA_URL="http://127.0.0.1:${GRAFANA_PORT}"

echo "[check] API health endpoint"
curl -fsS "${API_URL}/health" >/dev/null

echo "[check] API metrics endpoint with X-API-Key"
curl -fsS -H "X-API-Key: ${API_KEY}" "${API_URL}/metrics" \
  | python3 -c "import json,sys; data=json.load(sys.stdin); assert 'rows' in data and isinstance(data['rows'], list)"

echo "[check] API alerts endpoint with X-API-Key"
curl -fsS -H "X-API-Key: ${API_KEY}" "${API_URL}/alerts" \
  | python3 -c "import json,sys; data=json.load(sys.stdin); assert 'alerts' in data and isinstance(data['alerts'], list)"

echo "[check] Grafana health endpoint"
curl -fsS "${GRAFANA_URL}/api/health" \
  | python3 -c "import json,sys; data=json.load(sys.stdin); assert data.get('database') == 'ok'"

echo "[check] Generated artifacts on host"
test -s database/report/checkout_1_anomaly.csv
test -s database/report/checkout_2_anomaly.csv
test -s charts/checkout_1.svg
test -s charts/checkout_2.svg

echo "All one-click smoke checks passed."
