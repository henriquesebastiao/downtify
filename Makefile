#!make

DOWNTIFY_VERSION := 1.1.1
TARGET := henriquesebastiao/downtify

all: build latest

build:
	docker buildx create --use
	docker buildx build --platform=linux/amd64,linux/arm64 -t $(TARGET):$(DOWNTIFY_VERSION) --push .

latest:
	docker buildx create --use
	docker buildx build --platform=linux/amd64,linux/arm64 -t $(TARGET):latest --push .

clean:
	find downloads -type f -name "*.mp3" -exec rm -f {} \;

up:
	docker compose up --build -d

down:
	docker compose down

run:
	uv run python main.py web

format:
	uv run ruff format .; ruff check . --fix
	prettier --write frontend/src/.

lint:
	prettier --check frontend/src/.
	uv run ruff check .; ruff check . --diff

export:
	uv export --no-hashes --no-dev -o requirements.txt

changelog:
	github_changelog_generator -u henriquesebastiao -p downtify -o CHANGELOG --no-verbose
	@echo "Changelog generated at CHANGELOG"

.PHONY: all build latest clean up down run format lint export changelog