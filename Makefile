#!make

DOWNTIFY_VERSION := 3.0.0
TARGET := henriquesebastiao/downtify

all: build up

build:
	docker buildx build . --no-cache

clean:
	find downloads -type f -name "*.mp3" -exec rm -f {} \;

up:
	docker compose up --build -d

down:
	docker compose down
	docker rmi downtify:latest

run:
	uv run python main.py web

format:
	uv run ruff format .; ruff check . --fix
	prettier --write frontend/src/. docs/.vitepress/.

lint:
	prettier --check frontend/src/. docs/.vitepress/.
	uv run ruff check .; ruff check . --diff

export:
	uv export --no-hashes --no-dev -o requirements.txt

changelog:
	github_changelog_generator -u henriquesebastiao -p downtify -o CHANGELOG --no-verbose
	@echo "Changelog generated at CHANGELOG"

test:
	npm run test --prefix frontend
	npm run test --prefix docs
	uv run pytest -x -s -v

version:
	@VERSION=$(word 2,$(MAKECMDGOALS)); \
	echo "Downtify version: $$VERSION"; \
	./version.sh $$VERSION
	npm install --prefix frontend
	uv run ruff format .; ruff check . --fix
	prettier --write frontend/src/.

doc:
	npm install --prefix docs
	npm run dev --prefix docs

doc-build:
	npm ci --prefix docs
	npm run build --prefix docs

rm:
	sudo rm -rf docker/downloads/*
	sudo rm -rf docker/data/*

%:
	@:

.PHONY: all build clean up down run format lint export changelog version doc doc-build rm