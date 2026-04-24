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
  # Keep .env entries one-line and shell-safe for `source`.
  value="${value//$'\r'/}"
  value="${value//$'\n'/}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  local tmp_file
  tmp_file="$(mktemp)"
  awk -v key="${key}" -v value="${value}" '
    BEGIN { found = 0 }
    index($0, key "=") == 1 {
      print key "=" value
      found = 1
      next
    }
    { print }
    END {
      if (!found) {
        print key "=" value
      }
    }
  ' "${ENV_FILE}" > "${tmp_file}"
  mv "${tmp_file}" "${ENV_FILE}"
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

validate_env_file() {
  local env_path="$1"
  local invalid_lines
  invalid_lines="$(
    awk '
      /^[[:space:]]*($|#)/ { next }
      /^[A-Za-z_][A-Za-z0-9_]*=.*/ { next }
      { printf "%d:%s\n", NR, $0 }
    ' "${env_path}"
  )"
  if [[ -n "${invalid_lines}" ]]; then
    echo "Invalid env format detected in ${env_path}. Expected KEY=VALUE lines." >&2
    echo "${invalid_lines}" >&2
    exit 1
  fi
}

read_env_value() {
  local key="$1"
  local default_value="$2"
  local raw_value
  raw_value="$(
    awk -v key="${key}" '
      index($0, key "=") == 1 {
        print substr($0, length(key) + 2)
        exit
      }
    ' "${ENV_FILE}"
  )"
  raw_value="${raw_value//$'\r'/}"
  if [[ -z "${raw_value}" ]]; then
    printf '%s' "${default_value}"
    return
  fi
  if [[ "${raw_value}" == \"*\" && "${raw_value}" == *\" ]]; then
    raw_value="${raw_value:1:${#raw_value}-2}"
  elif [[ "${raw_value}" == \'*\' && "${raw_value}" == *\' ]]; then
    raw_value="${raw_value:1:${#raw_value}-2}"
  fi
  printf '%s' "${raw_value}"
}

is_port_available() {
  local port="$1"
  python - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("127.0.0.1", port))
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
}

pick_port() {
  local label="$1"
  local default_port="$2"
  local key="$3"
  local chosen_port="${default_port}"
  local max_tries=100
  local try_count=0

  while ! is_port_available "${chosen_port}"; do
    chosen_port="$((chosen_port + 1))"
    try_count="$((try_count + 1))"
    if (( try_count >= max_tries )); then
      echo "Could not find an available port for ${label} after ${max_tries} attempts starting from ${default_port}." >&2
      exit 1
    fi
  done

  write_env "${key}" "${chosen_port}"
  if [[ "${chosen_port}" != "${default_port}" ]]; then
    echo "[bootstrap] ${label} port ${default_port} is busy; using ${chosen_port}."
  fi
}

echo "CloudWalk reviewer bootstrap"
echo "This script prepares local config, starts containers, runs smoke checks, and prints first-login details."
echo "External AI is available as optional narrative polish. Local deterministic mode remains authoritative and fully valid for reviewer evaluation."

decision_mode="$(prompt_default "Decision mode (local/external)" "external")"
decision_mode="${decision_mode,,}"
if [[ "${decision_mode}" != "external" ]]; then
  decision_mode="local"
fi
write_env "DECISION_ENGINE_MODE" "${decision_mode}"

provider_label="local"
if [[ "${decision_mode}" == "external" ]]; then
  provider="$(prompt_default "External provider (openai/anthropic/google)" "openai")"
  provider="${provider,,}"
  base_url=""
  case "${provider}" in
    anthropic) example_model="claude-3-5-haiku-latest" ;;
    google) example_model="gemini-2.5-flash" ;;
    *) provider="openai"; example_model="gpt-4.1-mini" ;;
  esac
  if [[ "${provider}" == "openai" ]]; then
    base_url="$(prompt_default "OpenAI-compatible base URL (blank for official OpenAI)" "")"
  fi
  model="$(prompt_default "Model for ${provider}" "${example_model}")"
  api_key="$(prompt_hidden "API key for ${provider}")"
  if [[ -z "${api_key}" ]]; then
    echo "No external API key provided. Falling back to local deterministic mode."
    echo "Local mode remains fully functional and authoritative for reviewer evaluation; external AI is optional narrative polish."
    decision_mode="local"
    provider_label="local"
    write_env "DECISION_ENGINE_MODE" "local"
    write_env "EXTERNAL_AI_PROVIDER" ""
    write_env "EXTERNAL_AI_MODEL" ""
    write_env "EXTERNAL_AI_API_KEY" ""
    write_env "EXTERNAL_AI_BASE_URL" ""
  else
    provider_label="${provider}/${model}"
    write_env "EXTERNAL_AI_PROVIDER" "${provider}"
    write_env "EXTERNAL_AI_MODEL" "${model}"
    write_env "EXTERNAL_AI_API_KEY" "${api_key}"
    write_env "EXTERNAL_AI_BASE_URL" "${base_url}"
  fi
fi

use_demo="$(prompt_yes_no "Use demo-local API/Grafana credentials" "y")"
if [[ "${use_demo}" == "false" ]]; then
  grafana_password="$(prompt_hidden "Grafana admin password")"
  monitor_api_key="$(prompt_hidden "Monitoring API key")"
  write_env "GRAFANA_ADMIN_PASSWORD" "${grafana_password:-admin}"
  write_env "MONITORING_API_KEY" "${monitor_api_key:-${DEMO_API_KEY}}"
fi

team_webhook_url="$(prompt_hidden "Team notification webhook URL (blank for local mock receiver)")"
if [[ -z "${team_webhook_url}" ]]; then
  write_env "TEAM_NOTIFICATION_WEBHOOK_URL" ""
  team_notification_target_label="http://team-receiver:8010/notify"
else
  write_env "TEAM_NOTIFICATION_WEBHOOK_URL" "${team_webhook_url}"
  team_notification_target_label="configured in ${ENV_FILE} (TEAM_NOTIFICATION_WEBHOOK_URL)"
fi

anon_enabled="$(prompt_yes_no "Enable anonymous Grafana viewer mode" "y")"
write_env "GRAFANA_ANONYMOUS_ENABLED" "${anon_enabled}"

validate_env_file "${ENV_FILE}"

echo "[bootstrap] Cleaning up existing CloudWalk stack (if any)"
docker compose --env-file "${ENV_FILE}" down --remove-orphans >/dev/null 2>&1 || true

# Pick host ports dynamically when defaults are already in use to avoid startup failures.
pick_port "API" 8000 "API_PORT"
pick_port "Grafana" 3000 "GRAFANA_PORT"
pick_port "Team receiver" 8010 "TEAM_RECEIVER_PORT"

echo "[bootstrap] Starting stack"
docker compose --env-file "${ENV_FILE}" up --build -d

echo "[bootstrap] Running smoke checks"
api_port_value="$(read_env_value "API_PORT" "8000")"
grafana_port_value="$(read_env_value "GRAFANA_PORT" "3000")"
team_receiver_port_value="$(read_env_value "TEAM_RECEIVER_PORT" "8010")"
monitoring_api_key_value="$(read_env_value "MONITORING_API_KEY" "${DEMO_API_KEY}")"
decision_mode_value="$(read_env_value "DECISION_ENGINE_MODE" "local")"
anon_enabled_value="$(read_env_value "GRAFANA_ANONYMOUS_ENABLED" "true")"

MONITORING_API_KEY="${monitoring_api_key_value}" \
API_PORT="${api_port_value}" \
GRAFANA_PORT="${grafana_port_value}" \
TEAM_RECEIVER_PORT="${team_receiver_port_value}" \
"${ROOT_DIR}/scripts/smoke_one_click.sh"

printf '\nEnvironment ready.\n'
printf 'Grafana URL: http://127.0.0.1:%s\n' "${grafana_port_value}"
printf 'API URL: http://127.0.0.1:%s\n' "${api_port_value}"
printf 'Local team notification receiver: http://127.0.0.1:%s\n' "${team_receiver_port_value}"
printf 'Grafana user: %s\n' "${GRAFANA_ADMIN_USER:-admin}"
printf 'Grafana password: %s\n' "${GRAFANA_ADMIN_PASSWORD:-admin}"
if [[ "${monitoring_api_key_value}" == "${DEMO_API_KEY}" ]]; then
  printf 'Monitoring API key: %s\n' "${DEMO_API_KEY}"
else
  printf 'Monitoring API key: configured in %s (MONITORING_API_KEY)\n' "${ENV_FILE}"
fi
printf 'Decision mode: %s\n' "${decision_mode_value}"
printf 'Provider selection: %s\n' "${provider_label}"
if [[ "${decision_mode_value}" == "local" ]]; then
  printf 'Narrative mode: local deterministic explanations (authoritative for reviewer evaluation; external narrative polish disabled).\n'
else
  printf 'Narrative mode: external AI rewrite enabled as optional reviewer-facing narrative polish; local logic remains authoritative.\n'
fi
printf 'Dashboard refresh: fixed at 30 minutes.\n'
printf 'External AI note: when external mode is enabled, page loads and refresh cycles can trigger repeated AI-backed narrative requests because multiple panels query /decision/focus.\n'
printf 'Anonymous Grafana viewer mode: %s\n' "${anon_enabled_value}"
printf 'Team notification target: %s\n' "${team_notification_target_label}"
printf 'Local reviewer env file: %s\n' "${ENV_FILE}"
printf 'Stop command: docker compose --env-file %s down\n' "${ENV_FILE}"
