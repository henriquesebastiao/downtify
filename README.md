<h1 align="center">
  <a href="https://github.com/henriquesebastiao/downtify" target="_blank" rel="noopener noreferrer">
    <picture>
      <img width="80" src="assets/icon-without-backgroud.svg">
    </picture>
  </a>
  <br>
  Downtify
</h1>

<p align="center">Web GUI for <a href="https://github.com/spotDL/spotify-downloader">spotDL</a>. Allows you to download music from Spotify along with album art, lyrics and metadata.</p>

<div align="center">
  
[![Test](https://github.com/henriquesebastiao/downtify/actions/workflows/test.yml/badge.svg)](https://github.com/henriquesebastiao/downtify/actions/workflows/test.yml)
[![GitHub Release](https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=blue
)](https://github.com/henriquesebastiao/downtify/releases)
[![GitHub License](https://img.shields.io/github/license/henriquesebastiao/downtify?color=blue
)](/LICENSE)
[![Visitors](https://api.visitorbadge.io/api/visitors?path=henriquesebastiao%2Fdowntify&label=repository%20visits&countColor=%231182c3&style=flat)](https://github.com/henriquesebastiao/downtify)
[![Docker Pulls](https://img.shields.io/docker/pulls/henriquesebastiao/downtify?color=blue
)](https://hub.docker.com/r/henriquesebastiao/downtify)
  
</div>

https://github.com/user-attachments/assets/9711efe8-a960-4e1a-8d55-e0d1c20208f7

## Features ✨

With Downtify you can download Spotify music containing album art, track names, album title and other metadata about the songs. Just copy the Spotify link, whether it's a single song, an album, etc. As soon as your downloads are complete you will be notified!

## Music Sourcing

Downtify uses SpotDL to download music, which in turn uses YouTube as a download source. This method is used to avoid issues related to downloading music from Spotify.

> [!WARNING]
> Users are responsible for their actions and potential legal consequences. We do not support unauthorized downloading of copyrighted material and take no responsibility for user actions.

## Usage

### Docker CLI

> [!IMPORTANT]
> Make sure to change the path `/path/to/downloads` in the command below to the path on your computer where you want to view the downloaded songs.

```bash
docker run -d -p 8000:8000 --name downtify -v /path/to/downloads:/downloads henriquesebastiao/downtify
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
    environment:
      - DOWNTIFY_PORT=8000  # Optional
      - CLIENT_ID=5f573c9620494bae87890c0f08a60293  # Optional
      - CLIENT_SECRET=212476d9b0f3472eaa762d90b19b0ba8  # Optional
```

You can also set a custom port for the web interface via the `DOWNTIFY_PORT` environment variable in `docker-compose.yml`:


```yaml
ports:
  - '8000:30321'
environment:
  - DOWNTIFY_PORT=30321 
```

## License

This project is licensed under the [GPL-3.0](/LICENSE) License.
