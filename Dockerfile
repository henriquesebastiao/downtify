FROM python:3.13-alpine

LABEL maintainer="Henrique Sebastião <contato@henriquesebastiao.com>"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHON_COLORS=0

WORKDIR /downtify

COPY main.py requirements.txt ./
COPY templates ./templates

RUN pip install --no-cache-dir --root-user-action ignore -r requirements.txt \
    && spotdl --download-ffmpeg

VOLUME /downloads
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]