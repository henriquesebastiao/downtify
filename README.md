# Downtify

Web GUI for [spotDL](https://github.com/spotDL/spotify-downloader). Allows you to download music from Spotify along with album art, lyrics and metadata.

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
