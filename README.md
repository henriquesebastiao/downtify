<h1 align="center">
  <a href="https://preevy.dev" target="_blank" rel="noopener noreferrer">
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
[![GitHub Release](https://img.shields.io/github/v/release/henriquesebastiao/downtify)](https://github.com/henriquesebastiao/downtify/releases)
[![GitHub License](https://img.shields.io/github/license/henriquesebastiao/downtify)](/LICENSE)
[![Visitors](https://api.visitorbadge.io/api/visitors?path=henriquesebastiao%2Fdowntify&label=repository%20visits&countColor=%230d699c&style=flat)](https://github.com/henriquesebastiao/downtify)
[![Docker Pulls](https://img.shields.io/docker/pulls/henriquesebastiao/downtify)](https://hub.docker.com/r/henriquesebastiao/downtify)
  
</div>

https://github.com/user-attachments/assets/8840607a-8d89-4b90-84d4-b9a9b2137ad7

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
```

## License

This project is licensed under the [GPL-3.0](/LICENSE) License.
