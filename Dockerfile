FROM python:3.13-alpine

LABEL maintainer="Henrique Sebastião <contato@henriquesebastiao.com>"
LABEL version=${VERSION}
LABEL description="Self-hosted Spotify downloader"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHON_COLORS=0

ENV DOWNTIFY_PORT=8000
ENV DOWNTIFY_PATH="/"

WORKDIR /downtify

COPY main.py requirements-app.txt entrypoint.sh ./
COPY templates ./templates
COPY assets ./assets
COPY static ./static

RUN sed -i 's/\r$//g' entrypoint.sh && \
    chmod +x entrypoint.sh \
    && apk add --update shadow su-exec tini \
    && pip install --no-cache-dir --root-user-action ignore -r requirements-app.txt \
    && spotdl --download-ffmpeg \
    && cp /root/.spotdl/ffmpeg /downtify

ENV UID=1000
ENV GID=1000
ENV UMASK=022

ENV DOWNLOAD_DIR /downloads
VOLUME /downloads
EXPOSE ${DOWNTIFY_PORT}

ENTRYPOINT ["/sbin/tini", "-g", "--", "./entrypoint.sh"]