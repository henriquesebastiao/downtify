# Downtify ![Logo](https://github.com/user-attachments/assets/3653d889-5774-4acc-8c5d-a737e1638ab5)

[![Test](https://github.com/henriquesebastiao/downtify/actions/workflows/test.yml/badge.svg)](https://github.com/henriquesebastiao/downtify/actions/workflows/test.yml)
[![GitHub Release](https://img.shields.io/github/v/release/henriquesebastiao/downtify)](https://github.com/henriquesebastiao/downtify/releases)
[![GitHub License](https://img.shields.io/github/license/henriquesebastiao/downtify)](/LICENSE)
[![Docker Pulls](https://img.shields.io/docker/pulls/henriquesebastiao/downtify)](https://hub.docker.com/r/henriquesebastiao/downtify)

Web GUI for [spotDL](https://github.com/spotDL/spotify-downloader). Allows you to download music from Spotify along with album art, lyrics and metadata.

![screenshot](https://github.com/user-attachments/assets/734a30db-3057-46a0-9884-bfb95be990b0)

## Music Sourcing

Downtify uses SpotDL to download music, which in turn uses YouTube as a download source. This method is used to avoid issues related to downloading music from Spotify.

> [!WARNING]
> Users are responsible for their actions and potential legal consequences. We do not support unauthorized downloading of copyrighted material and take no responsibility for user actions.

## Usage

### Docker CLI

```bash
docker run -d -p 8000:8000 -v /path/to/downloads:/downloads henriquesebastiao/downtify
```

### Docker Compose

```yaml
services:
  downtify:
    container_name: downtify
    image: henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./path/to/downloads:/downloads
```

## License

This project is licensed under the [GPL-3.0](/LICENSE) License.
