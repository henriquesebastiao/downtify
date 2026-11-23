#!make

DOWNTIFY_VERSION := 3.14.0
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
	uv run pytest -x -s -v --cov=downtify && uv run coverage html

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

# Translation coverage of the docs; `make doc-i18n LOCALE=pt-BR` for one language.
doc-i18n:
	npm run i18n --prefix docs -- status $(LOCALE)

rm:
	sudo rm -rf docker/downloads/*
	sudo rm -rf docker/downloads/.*
	sudo rm -rf docker/data/*
	sudo rm -rf docker/data/.*

# The PostgreSQL service is opt-in (compose profile `postgres`).
db-up:
	docker compose --profile postgres up -d --wait postgres

# Copy an existing SQLite install into the compose PostgreSQL. Stop the app
# first (`make down`). The SQLite files in docker/data are never modified.
# Afterwards enable DATABASE_URL in docker-compose.yml.
db-migrate: db-up
	docker compose --profile postgres run --rm --no-deps --entrypoint python downtify main.py db-migrate --from-sqlite /data --to postgresql://downtify:$${POSTGRES_PASSWORD:-downtify}@postgres:5432/downtify

db-shell:
	docker compose exec postgres psql -U downtify downtify

db-backup:
	mkdir -p docker
	docker compose exec -T postgres pg_dump -U downtify downtify > docker/pg-backup-$$(date +%Y%m%d%H%M%S).sql

# DANGER: DELETES the PostgreSQL data volume (pgdata) and all data in it.
db-reset:
	docker compose --profile postgres down -v

update:
	uvx uv-bump
	npm --prefix frontend update -S
	uv export --no-hashes --no-dev -o requirements.txt

%:
	@:

.PHONY: all build clean up down run format lint export changelog version doc doc-build doc-i18n rm db-up db-migrate db-shell db-backup db-reset