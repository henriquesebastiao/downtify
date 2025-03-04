<h1 align="center">
  <a href="https://github.com/henriquesebastiao/downtify" target="_blank" rel="noopener noreferrer">
    <picture>
      <img width="80" src="images/icon-without-backgroud.svg">
    </picture>
  </a>
  <br>
  Downtify
</h1>

<p align="center">Web GUI for <a href="https://github.com/spotDL/spotify-downloader">spotDL</a>. Allows you to download music from Spotify along with album art, lyrics and metadata.</p>

<p align="center">
    <a href="https://coverage-badge.samuelcolvin.workers.dev/redirect/henriquesebastiao/downtify">
        <img src="https://github.com/henriquesebastiao/downtify/actions/workflows/test.yml/badge.svg" alt="Test"/>
    </a>
    <a href="https://codecov.io/gh/henriquesebastiao/skyport" > 
        <img src="https://coverage-badge.samuelcolvin.workers.dev/henriquesebastiao/downtify.svg" alt="Coverage Badge"/> 
    </a>
    <a href="https://raw.githubusercontent.com/henriquesebastiao/downtify/refs/heads/main/LICENSE">
        <img alt="LICENSE" src="https://img.shields.io/github/license/henriquesebastiao/downtify?color=blue"/>
    </a>
    <a href="https://github.com/henriquesebastiao/downtify">
        <img alt="Repository Visits" src="https://api.visitorbadge.io/api/visitors?path=henriquesebastiao%2Fdowntify&label=repository%20visits&countColor=%231182c3&style=flat"/>
    </a>
    <a href="https://hub.docker.com/r/henriquesebastiao/downtify">
        <img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/henriquesebastiao/downtify?color=blue"/>
    </a>
</p>

## Features ✨

With Downtify you can download Spotify music containing album art, track names, album title and other metadata about the songs. Just copy the Spotify link, whether it's a single song, an album, etc. As soon as your downloads are complete you will be notified!

## Music Sourcing

Downtify uses SpotDL to download music, which in turn uses YouTube as a download source. This method is used to avoid issues related to downloading music from Spotify.

!!! warning
    Users are responsible for their actions and potential legal consequences. We do not support unauthorized downloading of copyrighted material and take no responsibility for user actions.

## Usage

### Docker CLI

!!! tip
    Make sure to change the path `/path/to/downloads` in the command below to the path on your computer where you want to view the downloaded songs.

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

This project is licensed under the [GPL-3.0](https://raw.githubusercontent.com/henriquesebastiao/downtify/refs/heads/main/LICENSE) License.
