#!/usr/bin/env bash
# Build and push dx616b/spoti-to-navidrome to Docker Hub (local).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IMAGE="${IMAGE:-dx616b/spoti-to-navidrome}"
TAG="${TAG:-latest}"

if [[ ! -f frontend/dist/index.html ]]; then
  echo "building frontend/dist..."
  npm --prefix frontend ci
  npm --prefix frontend run build
fi

echo "logging in to Docker Hub (docker login if needed)..."
docker login

echo "building ${IMAGE}:${TAG} ..."
docker build -t "${IMAGE}:${TAG}" -t "${IMAGE}:latest" .

echo "pushing ${IMAGE}:${TAG} and ${IMAGE}:latest ..."
docker push "${IMAGE}:${TAG}"
docker push "${IMAGE}:latest"

echo "done: ${IMAGE}:${TAG}"
echo "deploy: TAG=${TAG} docker compose -f docker-compose.dockerhub.yml pull && docker compose up -d"
