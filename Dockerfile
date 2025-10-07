FROM python:3.13-alpine

LABEL maintainer="Henrique Sebastião <contato@henriquesebastiao.com>"
LABEL version="0.3.2"
LABEL description="Self-hosted Spotify downloader"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHON_COLORS=0

ENV DOWNTIFY_PORT=8000
ENV CLIENT_ID=5f573c9620494bae87890c0f08a60293
ENV CLIENT_SECRET=212476d9b0f3472eaa762d90b19b0ba8

WORKDIR /downtify

COPY main.py requirements-app.txt entrypoint.sh ./
COPY frontend/dist ./frontend/dist

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