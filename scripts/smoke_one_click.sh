#!/usr/bin/env bash
set -euo pipefail

API_PORT="${API_PORT:-8000}"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"
TEAM_RECEIVER_PORT="${TEAM_RECEIVER_PORT:-8010}"
API_KEY="${MONITORING_API_KEY:-reviewer-local-demo-key}"

API_URL="http://127.0.0.1:${API_PORT}"
GRAFANA_URL="http://127.0.0.1:${GRAFANA_PORT}"
TEAM_RECEIVER_URL="http://127.0.0.1:${TEAM_RECEIVER_PORT}"
API_CONTAINER_NAME="${API_CONTAINER_NAME:-cloudwalk-api}"

docker_exec() {
  MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker exec "$@"
}
# Inject at current UTC minute so reviewer startup always has recent data.
ALERT_TS="$(date -u +"%Y-%m-%d %H:%M:%S")"

echo "[check] API health endpoint"
curl -fsS "${API_URL}/health" >/dev/null

echo "[check] API metrics endpoint with X-API-Key"
curl -fsS -H "X-API-Key: ${API_KEY}" "${API_URL}/metrics" \
  | docker_exec -i "${API_CONTAINER_NAME}" python -c "import json,sys; data=json.load(sys.stdin); assert 'rows' in data and isinstance(data['rows'], list)"

echo "[check] API alerts endpoint with X-API-Key"
curl -fsS -H "X-API-Key: ${API_KEY}" "${API_URL}/alerts" \
  | docker_exec -i "${API_CONTAINER_NAME}" python -c "import json,sys; data=json.load(sys.stdin); assert 'alerts' in data and isinstance(data['alerts'], list)"

echo "[check] API decision endpoint with X-API-Key"
curl -fsS -H "X-API-Key: ${API_KEY}" "${API_URL}/decision" \
  | docker_exec -i "${API_CONTAINER_NAME}" python -c "import json,sys; data=json.load(sys.stdin); assert data['overall_status'] in {'normal','watch','act_now'}; assert isinstance(data['priority_items'], list); assert 'provider_status' in data"

echo "[check] Grafana health endpoint"
for attempt in $(seq 1 12); do
  if curl -fsS "${GRAFANA_URL}/api/health" 2>/dev/null \
    | docker_exec -i "${API_CONTAINER_NAME}" python -c "import json,sys; data=json.load(sys.stdin); assert data.get('database') == 'ok'" >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 12 ]]; then
    echo "Grafana health check failed after retries." >&2
    exit 1
  fi
  sleep 2
done

echo "[check] Team notification receiver health endpoint"
curl -fsS "${TEAM_RECEIVER_URL}/health" >/dev/null

echo "[check] Team notification delivery"
before_count="$(curl -fsS "${TEAM_RECEIVER_URL}/notifications" | docker_exec -i "${API_CONTAINER_NAME}" python -c "import json,sys; data=json.load(sys.stdin); print(len(data['notifications']))")"
curl -fsS -H "X-API-Key: ${API_KEY}" \
  -H "content-type: application/json" \
  -d "{\"window_end\":\"${ALERT_TS}\",\"approved\":100,\"denied\":54,\"failed\":1,\"reversed\":1,\"backend_reversed\":1,\"refunded\":1,\"auth_code_counts\":{\"51\":6,\"59\":3}}" \
  "${API_URL}/monitor" \
  | docker_exec -i "${API_CONTAINER_NAME}" python -c "import json,sys; data=json.load(sys.stdin); assert data['recommendation'] == 'alert'; assert data['team_notification_status'] in {'sent', 'failed', 'disabled'}"
after_count="$(curl -fsS "${TEAM_RECEIVER_URL}/notifications" | docker_exec -i "${API_CONTAINER_NAME}" python -c "import json,sys; data=json.load(sys.stdin); print(len(data['notifications']))")"
if (( after_count <= before_count )); then
  echo "Team notification delivery check failed: before=${before_count}, after=${after_count}" >&2
  exit 1
fi

echo "[check] Generated artifacts on host"
test -s database/report/checkout_1_anomaly.csv
test -s database/report/checkout_2_anomaly.csv
test -s charts/checkout_1.svg
test -s charts/checkout_2.svg

echo "[check] Grafana dashboard provisioning contract"
docker_exec "${API_CONTAINER_NAME}" python /app/scripts/check_grafana_dashboard_contract.py

echo "[check] Grafana dashboard Playwright validation (when tooling is available)"
./scripts/check_grafana_dashboard_playwright.sh

echo "All one-click smoke checks passed."
