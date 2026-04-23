#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_OPENSPEC="${ROOT_DIR}/.venv/bin/openspec"
ACTIVE_VENV_OPENSPEC="${VIRTUAL_ENV:-}/bin/openspec"
LOCAL_BIN_OPENSPEC="${HOME}/.local/bin/openspec"

if [[ -x "${VENV_OPENSPEC}" ]]; then
  exec "${VENV_OPENSPEC}" "$@"
fi

if [[ -n "${VIRTUAL_ENV:-}" && -x "${ACTIVE_VENV_OPENSPEC}" ]]; then
  exec "${ACTIVE_VENV_OPENSPEC}" "$@"
fi

if [[ -x "${LOCAL_BIN_OPENSPEC}" ]]; then
  exec "${LOCAL_BIN_OPENSPEC}" "$@"
fi

if command -v openspec >/dev/null 2>&1; then
  exec openspec "$@"
fi

echo "openspec CLI not found. Install into .venv or PATH." >&2
echo "Example: .venv/bin/pip install openspec" >&2
exit 1
