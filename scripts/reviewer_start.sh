#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_TEMPLATE="${ROOT_DIR}/.env.example"
ENV_FILE="${ROOT_DIR}/.env.reviewer"
DEMO_API_KEY="reviewer-local-demo-key"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but was not found on PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is required but was not found." >&2
  exit 1
fi

cp "${ENV_TEMPLATE}" "${ENV_FILE}"
chmod 600 "${ENV_FILE}"

write_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${ENV_FILE}"
  fi
}

prompt_default() {
  local message="$1"
  local default_value="$2"
  local input=""
  if [[ -t 0 ]]; then
    read -r -p "${message} [${default_value}]: " input
  fi
  printf '%s' "${input:-${default_value}}"
}

prompt_hidden() {
  local message="$1"
  local input=""
  if [[ -t 0 ]]; then
    read -r -s -p "${message}: " input
    printf '\n'
  fi
  printf '%s' "${input}"
}

prompt_yes_no() {
  local message="$1"
  local default_value="$2"
  local input=""
  if [[ -t 0 ]]; then
    read -r -p "${message} [${default_value}]: " input
  fi
  input="${input:-${default_value}}"
  case "${input,,}" in
    y|yes|true) printf 'true' ;;
    *) printf 'false' ;;
  esac
}

echo "CloudWalk reviewer bootstrap"
echo "This script prepares local config, starts containers, runs smoke checks, and prints first-login details."

decision_mode="$(prompt_default "Decision mode (local/external)" "local")"
decision_mode="${decision_mode,,}"
if [[ "${decision_mode}" != "external" ]]; then
  decision_mode="local"
fi
write_env "DECISION_ENGINE_MODE" "${decision_mode}"

provider_label="local"
if [[ "${decision_mode}" == "external" ]]; then
  provider="$(prompt_default "External provider (openai/anthropic/google)" "openai")"
  provider="${provider,,}"
  case "${provider}" in
    anthropic) example_model="claude-3-5-haiku-latest" ;;
    google) example_model="gemini-2.5-flash" ;;
    *) provider="openai"; example_model="gpt-4.1-mini" ;;
  esac
  model="$(prompt_default "Model for ${provider}" "${example_model}")"
  api_key="$(prompt_hidden "API key for ${provider}")"
  if [[ -z "${api_key}" ]]; then
    echo "No external API key provided. Falling back to local mode."
    decision_mode="local"
    provider_label="local"
    write_env "DECISION_ENGINE_MODE" "local"
    write_env "EXTERNAL_AI_PROVIDER" ""
    write_env "EXTERNAL_AI_MODEL" ""
    write_env "EXTERNAL_AI_API_KEY" ""
  else
    provider_label="${provider}/${model}"
    write_env "EXTERNAL_AI_PROVIDER" "${provider}"
    write_env "EXTERNAL_AI_MODEL" "${model}"
    write_env "EXTERNAL_AI_API_KEY" "${api_key}"
  fi
fi

use_demo="$(prompt_yes_no "Use demo-local API/Grafana credentials" "y")"
if [[ "${use_demo}" == "false" ]]; then
  grafana_password="$(prompt_hidden "Grafana admin password")"
  monitor_api_key="$(prompt_hidden "Monitoring API key")"
  write_env "GRAFANA_ADMIN_PASSWORD" "${grafana_password:-admin}"
  write_env "MONITORING_API_KEY" "${monitor_api_key:-${DEMO_API_KEY}}"
fi

anon_enabled="$(prompt_yes_no "Enable anonymous Grafana viewer mode" "y")"
write_env "GRAFANA_ANONYMOUS_ENABLED" "${anon_enabled}"

echo "[bootstrap] Starting stack"
docker compose --env-file "${ENV_FILE}" up --build -d

echo "[bootstrap] Running smoke checks"
set -a
. "${ENV_FILE}"
set +a
"${ROOT_DIR}/scripts/smoke_one_click.sh"

printf '\nEnvironment ready.\n'
printf 'Grafana URL: http://127.0.0.1:%s\n' "${GRAFANA_PORT:-3000}"
printf 'API URL: http://127.0.0.1:%s\n' "${API_PORT:-8000}"
printf 'Grafana user: %s\n' "${GRAFANA_ADMIN_USER:-admin}"
printf 'Grafana password: %s\n' "${GRAFANA_ADMIN_PASSWORD:-admin}"
if [[ "${MONITORING_API_KEY:-${DEMO_API_KEY}}" == "${DEMO_API_KEY}" ]]; then
  printf 'Monitoring API key: %s\n' "${DEMO_API_KEY}"
else
  printf 'Monitoring API key: configured in %s (MONITORING_API_KEY)\n' "${ENV_FILE}"
fi
printf 'Decision mode: %s\n' "${DECISION_ENGINE_MODE:-local}"
printf 'Provider selection: %s\n' "${provider_label}"
printf 'Anonymous Grafana viewer mode: %s\n' "${GRAFANA_ANONYMOUS_ENABLED:-true}"
printf 'Local reviewer env file: %s\n' "${ENV_FILE}"
printf 'Stop command: docker compose --env-file %s down\n' "${ENV_FILE}"
