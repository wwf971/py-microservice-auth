#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PORT="${PORT:-9530}"
is_dry_run=false

if [[ "${1:-}" == "--dry-run" ]]; then
  is_dry_run=true
fi

free_port_if_needed() {
  local port="$1"
  local isDryRun="$2"
  local try_index=0
  local max_try=8

  is_port_bindable() {
    local test_port="$1"
    python3 - <<'PY' "$test_port"
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind(("0.0.0.0", port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
sys.exit(0)
PY
  }

  while (( try_index < max_try )); do
    if is_port_bindable "$port"; then
      return 0
    fi

    local pidsText
    pidsText="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -z "$pidsText" ]]; then
      pidsText="$(lsof -tiTCP:"$port" 2>/dev/null || true)"
    fi

    if [[ -n "$pidsText" ]]; then
      echo "Port $port is occupied. Existing pid(s):"
      echo "$pidsText"
      if [[ "$isDryRun" == true ]]; then
        echo "Dry run: would kill pid(s) on port $port"
        return 0
      fi
      echo "Killing pid(s) on port $port"
      while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        if (( try_index < max_try - 2 )); then
          kill "$pid" >/dev/null 2>&1 || true
        else
          kill -9 "$pid" >/dev/null 2>&1 || true
        fi
      done <<< "$pidsText"
    fi

    sleep 0.25
    try_index=$((try_index + 1))
  done

  if is_port_bindable "$port"; then
    return 0
  fi
  echo "Failed to free port $port after retries."
  return 1
}

echo "launch-test root: $ROOT_DIR"
echo "DIR_BASE: $ROOT_DIR"
echo "PORT: $BACKEND_PORT"
echo "Visit: http://localhost:$BACKEND_PORT/manage/"

for port in "$BACKEND_PORT" "$((BACKEND_PORT + 1))" "$((BACKEND_PORT + 2))" "$((BACKEND_PORT + 3))"; do
  free_port_if_needed "$port" "$is_dry_run"
done

if [[ "$is_dry_run" == true ]]; then
  echo "Dry run: would compile proto: bash \"$ROOT_DIR/script/compile_proto.sh\""
  echo "Dry run: would run frontend build: pnpm --dir \"$FRONTEND_DIR\" run build"
  echo "Dry run: would run local server: PORT=\"$BACKEND_PORT\" DIR_BASE=\"$ROOT_DIR\" bash \"$ROOT_DIR/script/start-dev.sh\""
  exit 0
fi

bash "$ROOT_DIR/script/compile_proto.sh"
pnpm --dir "$FRONTEND_DIR" install
pnpm --dir "$FRONTEND_DIR" run build
exec env PORT="$BACKEND_PORT" DIR_BASE="$ROOT_DIR" bash "$ROOT_DIR/script/start-dev.sh"
