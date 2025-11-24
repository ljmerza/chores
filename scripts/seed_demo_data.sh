#!/usr/bin/env bash
set -euo pipefail

# Run the demo seed command either inside the docker-compose web service (if available)
# or locally as a fallback. Pass any extra args (e.g., --force) straight through.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

compose_cmd() {
  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return
  fi
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return
  fi
  echo ""
}

COMPOSE=$(compose_cmd)
PYTHON_BIN_LOCAL="$ROOT_DIR/venv/bin/python"
if [ ! -x "$PYTHON_BIN_LOCAL" ]; then
  PYTHON_BIN_LOCAL="python"
fi
# Inside the container we default to the system python in the image.
PYTHON_BIN_DOCKER="python"

if [ -n "$COMPOSE" ]; then
  services=$($COMPOSE ps --services 2>/dev/null || true)
  if echo "$services" | grep -q "^web$"; then
    echo "Running seed inside docker web service..."
    exec $COMPOSE exec web $PYTHON_BIN_DOCKER manage.py seed_demo_data "$@"
  fi
fi

echo "Running seed locally (docker web service not detected)..."
exec "$PYTHON_BIN_LOCAL" manage.py seed_demo_data "$@"
