---
icon: lucide/route
---

# Outbound proxy

Downtify can send supported outbound HTTP traffic through an HTTP, HTTPS or SOCKS5 proxy. This is configured with environment variables, not in Settings.

## Configure

Set `DOWNTIFY_PROXY` to one proxy URL. It accepts `http://`, `https://`, `socks5://` and `socks5h://`, including URL-encoded credentials. `socks5h` keeps destination DNS resolution on the proxy.

If `DOWNTIFY_PROXY` is unset, Downtify uses the standard `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` and lowercase equivalents. `DOWNTIFY_PROXY` takes precedence and supplies the same proxy for HTTP and HTTPS.

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNTIFY_PROXY` | _(unset)_ | HTTP, HTTPS or SOCKS5 proxy URL for outbound requests. |
| `DOWNTIFY_PROXY_STRICT` | `false` | `true` requires a proxy for both HTTP and HTTPS (or `ALL_PROXY`) and stops startup when coverage is incomplete. Connection failures do not retry directly. |
| `DOWNTIFY_PROXY_BYPASS` | _(unset)_ | Comma-separated hostnames, domains or IP ranges to add to `NO_PROXY`, for services deliberately reached directly. `localhost`, `127.0.0.1` and `::1` are also bypassed whenever a proxy is configured. |

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    environment:
      DOWNTIFY_PROXY: socks5h://tor-gateway:9050
      DOWNTIFY_PROXY_STRICT: 'true'
      DOWNTIFY_PROXY_BYPASS: slskd,navidrome
```

The proxy service must be reachable from Downtify's Docker network. Add the configured slskd or Navidrome hostnames to the bypass list when those services should stay on the local network. Existing `NO_PROXY` entries are preserved.

## Check the route

An admin can call `POST /api/proxy/test`. It checks the configured proxy against the Tor Project's status endpoint and reports whether the request was reachable and whether the exit was recognized as Tor. It never returns or logs the public IP. It does not make a direct request when no proxy is configured or when the test host is bypassed.

## Coverage and limits

Proxy settings apply to Downtify's HTTPX requests (including Spotify, Deezer, Apple/iTunes, cover art, lyrics, OIDC and update checks), YouTube Music's Requests session, and yt-dlp downloads and stream resolution. SOCKS dependencies are included in the Docker image. HTTPX receives `socks5://` for a `socks5h://` URL; its SOCKS transport sends the destination hostname to the proxy, so DNS remains remote. YouTube Music and yt-dlp retain the original `socks5h` URL.

Strict mode covers these supported HTTP transports; it cannot constrain arbitrary sockets opened by future or third-party code. A Docker or host firewall that denies direct egress is the only network-layer guarantee. An explicit `NO_PROXY` or `DOWNTIFY_PROXY_BYPASS` entry is an intentional direct route, including in strict mode.

A working proxy does not guarantee that an upstream service will answer or return the same data. Providers may rate-limit or reject proxy/Tor traffic. In particular, yt-dlp's warning about missing YouTube formats points to [a YouTube SABR-format issue](https://github.com/yt-dlp/yt-dlp/issues/12482), not a proxy routing failure.

The container healthcheck always probes its own localhost server without using the configured proxy.