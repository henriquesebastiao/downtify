#!make

DOWNTIFY_VERSION := 0.3.2
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

.PHONY: all build latest clean up down