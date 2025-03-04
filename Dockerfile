FROM python:3.13-alpine

LABEL maintainer="Henrique Sebastião <contato@henriquesebastiao.com>"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHON_COLORS=0

WORKDIR /downtify

COPY main.py requirements.txt entrypoint.sh ./
COPY templates ./templates
COPY assets ./assets
COPY static ./static

RUN sed -i 's/\r$//g' entrypoint.sh && \
    chmod +x entrypoint.sh \
    && apk add --update ffmpeg shadow su-exec tini \
    && pip install --no-cache-dir --root-user-action ignore -r requirements.txt \
    && spotdl --download-ffmpeg

ENV UID=1000
ENV GID=1000
ENV UMASK=022

ENV DOWNLOAD_DIR /downloads
VOLUME /downloads
EXPOSE 8000

ENTRYPOINT ["/sbin/tini", "-g", "--", "./entrypoint.sh"]