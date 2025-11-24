#!/usr/bin/env bash
set -euo pipefail

# Run Django makemigrations inside the docker web service when available, otherwise fallback to local.
# Extra args are passed straight to `manage.py makemigrations` (e.g., app labels).

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
PYTHON_BIN_DOCKER="python"

if [ -n "$COMPOSE" ]; then
  services=$($COMPOSE ps --services 2>/dev/null || true)
  if echo "$services" | grep -q "^web$"; then
    container_running=$($COMPOSE ps -q web 2>/dev/null || true)
    if [ -n "$container_running" ]; then
      echo "Running makemigrations inside existing docker web service..."
      exec $COMPOSE exec web $PYTHON_BIN_DOCKER manage.py makemigrations "$@"
    fi
  fi
  echo "Running makemigrations in a one-off docker web container..."
  exec $COMPOSE run --rm web $PYTHON_BIN_DOCKER manage.py makemigrations "$@"
fi

echo "Running makemigrations locally (docker compose not detected)..."
exec "$PYTHON_BIN_LOCAL" manage.py makemigrations "$@"
