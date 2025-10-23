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

## Features

With Downtify you can download Spotify music containing album art, track names, album title and other metadata about the songs. Just copy the Spotify link, whether it's a single song, an album, etc. As soon as your downloads are complete you will be notified!

### Playlist Monitoring

Downtify now supports automatic monitoring of Spotify playlists to detect and download new songs:

- **Automatic Detection**: Monitor playlists for new tracks added on Spotify
- **Auto-Download**: Automatically download newly added tracks
- **Scheduled Checks**: Periodic checks with configurable interval (default: 1 hour)
- **Simple Management**: API endpoints to add, remove, and list monitored playlists

See a demo of Downtify at: [https://downtify.henriquesebastiao.com](https://downtify.henriquesebastiao.com/)

## Music Sourcing

Downtify uses [SpotDL](https://github.com/spotDL/spotify-downloader) to download music, which in turn uses YouTube as a download source. This method is used to avoid issues related to downloading music from Spotify.

> [!WARNING]
> Users are responsible for their actions and potential legal consequences. We do not support unauthorized downloading of copyrighted material and take no responsibility for user actions.

## Usage

### Docker CLI

> [!IMPORTANT]
> Make sure to change the path `/path/to/downloads` in the command below to the path on your computer where you want to view the downloaded songs.

```bash
docker run -d -p 8000:8000 --name downtify -v /path/to/downloads:/downloads ghcr.io/henriquesebastiao/downtify
```

### Docker Compose

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./path/to/downloads:/downloads
```

Change the value `./path/to/downloads` to the directory on your machine where you want the downloaded songs to be saved.

Now you can access Downtify at http://localhost:8000/

You can also set a custom port for the web interface via the `DOWNTIFY_PORT` environment variable in `docker-compose.yml`:

```yaml
ports:
  - '8000:30321'
environment:
  - DOWNTIFY_PORT=30321 
```

### Playlist Monitoring Configuration

To configure playlist monitoring, you can set the following environment variables:

```yaml
environment:
  - MONITOR_INTERVAL=3600  # Check interval in seconds (default: 1 hour)
  - MONITOR_STORAGE=/downloads/.monitored_playlists.json  # Storage file path
```

**API Endpoints:**

- `POST /monitor/add?playlist_url=<url>` - Add a playlist to monitoring
- `DELETE /monitor/remove?playlist_url=<url>` - Remove a playlist from monitoring
- `GET /monitor/list` - List all monitored playlists
- `POST /monitor/check` - Manually trigger a check for all monitored playlists

**Example Usage:**

```bash
# Add a playlist to monitoring
curl -X POST "http://localhost:8000/monitor/add?playlist_url=https://open.spotify.com/playlist/YOUR_PLAYLIST_ID"

# List monitored playlists
curl "http://localhost:8000/monitor/list"

# Remove a playlist from monitoring
curl -X DELETE "http://localhost:8000/monitor/remove?playlist_url=https://open.spotify.com/playlist/YOUR_PLAYLIST_ID"
```

## Available in the app stores of home server OS

Downtify is also available in the app store of self-hosted home server operating systems such as:

- [Umbrel](https://apps.umbrel.com/app/downtify) ☂️
- [CasaOS](https://casaos.zimaspace.com/)
- [HomeDock OS](https://www.homedock.cloud/apps/downtify/)

## Possible problems and solutions

**Problem:** Downtify cannot download music, error: `application has reached a rate/request limit`.

**Quick Fix: Use Your Own Client ID and Secret**

To avoid these issues, we recommend using your own client ID and secret from Spotify. Here’s how:

1. **Visit the Spotify Developer Dashboard**: Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. **Log In**: Sign in or create a Spotify account.
3. **Create a New App**: Click "Create an App" and fill in the details. (Set APIs used to Web API and Redirect URIs to `http://127.0.0.1:9900/` (or whatever you want to use))
4. **Get Your Credentials**: Copy your client ID and secret.

**Run Downtify passing your client ID and client secret as environment variables:**

Docker CLI:

```bash
docker run -d -p 8000:8000 --name downtify -v /path/to/downloads:/downloads -e CLIENT_ID=your_client_id -e CLIENT_SECRET=your_client_secret ghcr.io/henriquesebastiao/downtify
```

Docker Compose:

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./path/to/downloads:/downloads
    environment:
      - CLIENT_ID=your_client_id
      - CLIENT_SECRET=your_client_secret
```

Replace `your_client_id` and `your_client_secret` with the values you obtained from Spotify.

## License

This project is licensed under the [GPL-3.0](/LICENSE) License.
