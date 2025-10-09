FROM python:3.13-alpine AS builder

WORKDIR /build

COPY requirements-app.txt .

RUN pip install --no-cache-dir --root-user-action ignore -r requirements-app.txt && \
    spotdl --download-ffmpeg && \
    cp /root/.spotdl/ffmpeg /build/ffmpeg

FROM python:3.13-alpine

LABEL maintainer="Henrique Sebastião <contato@henriquesebastiao.com>"
LABEL version="1.0.0"
LABEL description="Self-hosted Spotify downloader"

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

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${DOWNTIFY_PORT}/ || exit 1

ENTRYPOINT ["/sbin/tini", "-g", "--", "./entrypoint.sh"]