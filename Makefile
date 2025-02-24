#!make

DOWNTIFY_VERSION := 0.2.2
TARGET := henriquesebastiao/downtify

all: build latest

build:
	docker buildx create --use
	docker buildx build --platform=linux/amd64,linux/arm64 -t $(TARGET):$(DOWNTIFY_VERSION) --push .

latest:
	docker buildx create --use
	docker buildx build --platform=linux/amd64,linux/arm64 -t $(TARGET):latest --push .

.PHONY: all build latest