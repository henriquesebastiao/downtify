---
icon: lucide/route
---

# 出站代理

Downtify 可以通过 HTTP、HTTPS 或 SOCKS5 代理发送受支持的出站 HTTP 流量。代理通过环境变量配置，而不是在 Settings 中设置。

## 配置

将 `DOWNTIFY_PROXY` 设置为一个代理 URL。支持 `http://`、`https://`、`socks5://` 和 `socks5h://`，包括经过 URL 编码的凭据。`socks5h` 会将目标 DNS 解析交给代理执行。

如果未设置 `DOWNTIFY_PROXY`，Downtify 会使用标准变量 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 及其小写形式。`DOWNTIFY_PROXY` 优先级更高，并为 HTTP 和 HTTPS 使用同一个代理。

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `DOWNTIFY_PROXY` | _(未设置)_ | 出站请求使用的 HTTP、HTTPS 或 SOCKS5 代理 URL。 |
| `DOWNTIFY_PROXY_STRICT` | `false` | 设为 `true` 后，HTTP 和 HTTPS（或 `ALL_PROXY`）都必须配置代理；覆盖不完整时停止启动。连接失败时不会改为直连重试。 |
| `DOWNTIFY_PROXY_BYPASS` | _(未设置)_ | 以逗号分隔的主机名、域名或 IP 网段，追加到 `NO_PROXY`，用于指定应直接访问的服务。配置代理后，`localhost`、`127.0.0.1` 和 `::1` 也会绕过代理。 |

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    environment:
      DOWNTIFY_PROXY: socks5h://tor-gateway:9050
      DOWNTIFY_PROXY_STRICT: 'true'
      DOWNTIFY_PROXY_BYPASS: slskd,navidrome
```

代理服务必须能从 Downtify 所在的 Docker 网络访问。如果 slskd 或 Navidrome 应通过本地网络访问，请将其配置的主机名加入绕过列表。已有的 `NO_PROXY` 条目会保留。

## 检查代理路由

管理员可以调用 `POST /api/proxy/test`。该接口使用 Tor Project 的状态端点测试已配置代理，并报告请求是否可达、出口节点是否被识别为 Tor。它不会返回或记录公网 IP。如果未配置代理，或测试主机在绕过列表中，则不会发起直连请求。

## 覆盖范围与限制

代理设置适用于 Downtify 的 HTTPX 请求（包括 Spotify、Deezer、Apple/iTunes、封面、歌词、OIDC 和更新检查）、YouTube Music 的 Requests 会话，以及 yt-dlp 下载和流解析。Docker 镜像中已包含 SOCKS 所需依赖。对于 `socks5h://` URL，HTTPX 使用 `socks5://`；其 SOCKS 传输仍会将目标主机名交给代理，因此 DNS 解析仍在代理侧进行。YouTube Music 和 yt-dlp 则保留原始 `socks5h` URL。

严格模式覆盖这些受支持的 HTTP 传输，但不能约束未来或第三方代码打开的任意套接字。只有通过 Docker 或主机防火墙禁止直连出站流量，才能在网络层面提供保证。明确配置的 `NO_PROXY` 或 `DOWNTIFY_PROXY_BYPASS` 条目属于有意直连，即使启用严格模式也一样。

代理正常工作并不保证上游服务一定响应或返回相同数据。服务提供方可能会对代理或 Tor 流量限流或拒绝请求。尤其是 yt-dlp 提示缺少 YouTube 格式时，原因通常是 [YouTube SABR 格式问题](https://github.com/yt-dlp/yt-dlp/issues/12482)，而非代理路由失败。

容器健康检查始终通过 localhost 检查 Downtify 自身服务器，不会使用已配置的代理。
