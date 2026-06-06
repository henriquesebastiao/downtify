#!/usr/bin/env bash
# Build and smoke-test the local docker-compose stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing: $1" >&2
    exit 1
  fi
}

need docker
need make
docker compose version >/dev/null

mkdir -p docker/downloads docker/data

if [[ ! -f frontend/dist/index.html ]]; then
  echo "building frontend/dist..."
  npm --prefix frontend ci
  npm --prefix frontend run build
fi

echo "starting container..."
make down 2>/dev/null || true
make up

echo "waiting for API..."
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:8000/api/version" >/tmp/downtify-version.json 2>/dev/null \
    && curl -fsS -o /dev/null "http://127.0.0.1:8000/" 2>/dev/null; then
    echo "API OK:"
    cat /tmp/downtify-version.json
    echo "SPA OK: http://127.0.0.1:8000/"
    docker compose ps
    echo "done (container left running; use: make down)"
    exit 0
  fi
  sleep 2
done

echo "container did not become healthy in time" >&2
docker compose logs --tail 80 downtify
exit 1
