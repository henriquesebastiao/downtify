FROM python:3.14-alpine AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --no-cache-dir --root-user-action ignore -r requirements.txt && \
    spotdl --download-ffmpeg && \
    cp /root/.config/spotdl/ffmpeg /build/ffmpeg

FROM python:3.14-alpine

LABEL maintainer="Henrique Sebastião <contato@henriquesebastiao.com>"
LABEL version="1.0.1"
LABEL description="Self-hosted Spotify downloader"

LABEL org.opencontainers.image.title="Downtify" \
      org.opencontainers.image.description="Download your Spotify playlists and songs along with album art and metadata in a self-hosted way via Docker." \
      org.opencontainers.image.version="1.0.1" \
      org.opencontainers.image.authors="Henrique Sebastião <contato@henriquesebastiao.com>" \
      org.opencontainers.image.url="https://github.com/henriquesebastiao/downtify" \
      org.opencontainers.image.source="https://github.com/henriquesebastiao/downtify" \
      org.opencontainers.image.licenses="GPL-3.0" \
      org.opencontainers.image.documentation="https://github.com/henriquesebastiao/downtify#readme" \
      org.opencontainers.image.vendor="Henrique Sebastião" \
      org.opencontainers.image.base.name="python:3.13-alpine"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHON_COLORS=0 \
    DOWNTIFY_PORT=8000 \
    UID=1000 \
    GID=1000 \
    UMASK=022

WORKDIR /downtify

RUN apk add --no-cache \
    shadow \
    su-exec \
    tini

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /build/ffmpeg /usr/local/bin/ffmpeg

COPY main.py entrypoint.sh ./
COPY frontend/dist ./frontend/dist

RUN sed -i 's/\r$//g' entrypoint.sh && \
    chmod +x entrypoint.sh

ENV PATH="/home/downtify/.local/bin:${PATH}"

VOLUME /downloads
EXPOSE ${DOWNTIFY_PORT}

ENTRYPOINT ["/sbin/tini", "-g", "--", "./entrypoint.sh"]