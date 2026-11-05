---
icon: lucide/settings
---

# 环境变量

所有环境变量均为可选项。即使不设置任何变量，Downtify 也能直接运行。

## 核心设置

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `DOWNTIFY_PORT` | _(unset)_ | 服务器在容器内监听的端口。未设置时使用 **Settings → Server → Port** 中选择的端口，否则为 `8000`。设置后以此值为准，且设置页的端口选项会锁定。要更改主机对外端口，请修改端口映射左侧。详见[更改端口](../features/server.md#changing-the-port)。 |
| `DOWNLOAD_DIR` | `/downloads` | 保存音频文件的目录。如果将媒体库挂载到自定义路径，可在此覆盖默认值。 |
| `HOST` | `0.0.0.0` | Web 服务器的绑定地址。 |
| `DOWNTIFY_LOG_LEVEL` | `info` | 应用日志级别（`debug`、`info`、`warning` 等）。 |
| `TZ` | `UTC` | 本地时区（IANA 名称，例如 `America/Sao_Paulo`），用于解析下方的 `DOWNTIFY_MONITOR_SYNC_TIME`。 |

## 播放列表监控

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `DOWNTIFY_MONITOR_SYNC_TIME` | _(unset)_ | [播放列表监控](../features/playlist-monitor.md#choosing-a-daily-sync-time)按天或更长间隔（每天、每周、每两周、每月）同步时的执行时间。格式为 24 小时制 `HH:MM`，使用上方 `TZ` 指定的时区。留空时，会在上次检查后经过一个完整间隔再同步。 |

```yaml
environment:
  - TZ=America/Sao_Paulo
  - DOWNTIFY_MONITOR_SYNC_TIME=03:00
```

## 移动应用与登录

请参阅[移动应用](../features/mobile-apps.md)和[用户与登录](../features/users.md)。除非将 `DOWNTIFY_DISABLE_AUTH` 设为 `true`，否则必须登录。旧版本中的 `DOWNTIFY_REQUIRE_SIGN_IN` 已不再使用；如果仍设置该变量，日志会显示警告。

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `DOWNTIFY_DISABLE_AUTH` | `false` | 设为 `true` 后关闭账号功能：无需登录，任何能访问服务器的人都将以管理员身份使用。登录页、退出登录按钮、**Settings → Users** 以及 **Settings → General** 中的账号设置都会隐藏。已配对的应用仍可使用。改回 `false`（或移除此变量）后会恢复登录要求，原有账号也会保留。详见[关闭账号](../features/users.md#turning-accounts-off)。 |
| `DOWNTIFY_DISABLE_LOCAL_LOGIN` | `false` | 设为 `true` 后，禁用 Web 界面及 `POST /api/auth/token` 的用户名/密码登录。OIDC 和应用配对仍可使用；现有会话和设备令牌不会撤销。必须同时配置下方全部三个 OIDC 凭据。 |
| `DOWNTIFY_OIDC_ISSUER` | _(unset)_ | 完整的 OIDC issuer URL。与客户端 ID 和密钥一同设置后启用 OIDC。 |
| `DOWNTIFY_OIDC_CLIENT_ID` | _(unset)_ | OIDC confidential client ID。 |
| `DOWNTIFY_OIDC_CLIENT_SECRET` | _(unset)_ | OIDC confidential client secret。 |
| `DOWNTIFY_OIDC_REDIRECT_URI` | _(derived)_ | 在身份提供商中注册的公开回调 URL，通常为 `https://music.example.com/api/auth/oidc/callback`。如使用反向代理，必要时请显式设置。 |
| `DOWNTIFY_OIDC_SCOPES` | `openid profile email` | 以空格分隔的 OIDC scope 列表。 |
| `DOWNTIFY_OIDC_USERNAME_CLAIM` | `preferred_username` | 用于新账号名称的 claim；若不存在，则依次回退到 `email` 和 `sub`。 |
| `DOWNTIFY_OIDC_GROUPS_CLAIM` | `groups` | 包含组名的 claim；支持点分隔的路径。 |
| `DOWNTIFY_OIDC_ALLOWED_GROUPS` | _(empty)_ | 以逗号分隔的允许登录组列表。留空时，任何通过身份验证的提供方用户都可以登录。 |
| `DOWNTIFY_OIDC_ADMIN_GROUPS` | _(empty)_ | 映射为 Downtify 管理员的组名，以逗号分隔。其他 OIDC 用户将作为普通用户。 |
| `DOWNTIFY_TRUSTED_PROXIES` | _(unset)_ | 反向代理的地址或网段列表，以逗号分隔（例如 `172.18.0.0/16,10.0.0.5`）。仅信任来自这些地址的请求所携带的 `X-Forwarded-For`、`X-Forwarded-Proto` 和 `X-Forwarded-Host`，用于识别客户端地址、限制登录和配对尝试频率、设置登录 Cookie 的安全标志并执行 same-site 检查。未设置时会忽略这些请求头。 |
| `DOWNTIFY_DISCOVERY` | `true` | 设为 `false` 后，停止通过本地网络 mDNS（`_downtify._tcp`）广播服务器；应用依靠该广播在 *Found on this network* 列表中显示服务器。在 Docker bridge 网络中，广播本来也无法到达局域网。详见 [Docker Compose](docker-compose.md#finding-the-server-from-the-apps)。 |
| `DOWNTIFY_TRANSCODE_CACHE_MB` | `2048` | 转码副本缓存（`/data/transcode_cache`）的最大大小，单位为 MB；优先清除最近较少播放的副本。 |
| `DOWNTIFY_TRANSCODE_CONCURRENCY` | `2` | 同时为应用的较低流媒体音质转码的歌曲数量。 |
| `DOWNTIFY_STREAM_CACHE_MB` | `1024` | 流式音频缓存（`/data/stream_cache`）的最大大小，单位为 MB；优先清除最近较少播放的副本。通过服务器转流，可播放浏览器本身无法访问 YouTube 的未下载曲目。 |
| `DOWNTIFY_STREAM_CONCURRENCY` | `2` | 同时运行的流媒体下载任务数。 |

OIDC 为可选功能。请同时配置 issuer、客户端 ID 和密钥；只配置其中一部分会导致服务无法启动。身份提供商必须允许回调 URL `https://<your-public-host>/api/auth/oidc/callback`。账号关联、组映射及本地登录选项详见 [OpenID Connect](../features/users.md#openid-connect)。

## 音乐回收站

请参阅[音乐回收站](../features/music-trash.md)。除非设置以下变量之一，否则此功能默认关闭。

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `DOWNTIFY_TRASH` | `false` | 设为 `true` 后为下载目录启用音乐回收站：删除歌曲时由 Downtify 将文件移入回收站，并保留 30 天。启用期间只有管理员可以删除歌曲。 |
| `DOWNTIFY_TRASH_CONFIG` | _(unset)_ | 容器内 JSON 配置文件的路径。文件列出回收站覆盖的目录以及工作进程运行方式（`embedded` 或 `external`）。优先级高于 `DOWNTIFY_TRASH`。文件无法读取时，服务器会在启动时退出。详见[配置文件](../features/music-trash.md#the-configuration-file)。 |

## 健康检查

镜像内置 [Docker `HEALTHCHECK`](https://docs.docker.com/reference/dockerfile/#healthcheck)，无需自定义 `--health-cmd`。它每 30 秒通过容器自身端口轮询 `GET /api/health`（超时 5 秒，启动宽限期 20 秒，连续失败 3 次后标记为不健康）。可通过 `docker ps` 和 `docker inspect` 查看结果，Compose 的 `condition: service_healthy` 或 Watchtower 等工具也可据此采取操作。

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `DOWNTIFY_HEALTHCHECK` | `1` | 设为 `0` 可禁用内置检查；禁用后不会联系服务器，而是始终报告健康。如果只希望由外部系统或编排平台（例如 Kubernetes liveness probe）判断容器健康状态，可使用此选项。 |

```yaml
environment:
  - DOWNTIFY_HEALTHCHECK=0
```

## 反机器人验证 / YouTube

YouTube 会定期对自动下载工具发起验证。默认配置失效时，可以尝试通过以下变量调整行为。

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(unset)_ | 设为 `1` 可强制 yt-dlp 仅使用 IPv4。当主机的 IPv6 不可用或受到限流时，此选项会很有帮助。 |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | 按顺序尝试的 yt-dlp 播放器客户端列表，以逗号分隔。Downtify 默认优先使用无需 JavaScript 运行时的客户端。只有确认特定客户端遭到屏蔽时才建议覆盖此设置。 |
| `DOWNTIFY_YT_PO_TOKEN` | _(unset)_ | 提供给 yt-dlp 的 Proof-of-Origin token 列表，以逗号分隔，每项格式为 `<client>.<context>+<token>`（例如 `mweb.gvs+ABC123`）。仅当 YouTube 开始要求当前客户端提供 PO Token 时才需要设置。 |
| `DOWNTIFY_COOKIES_FILE` | _(unset)_ | 容器**内部** Netscape 格式 `cookies.txt` 的路径。让 yt-dlp 使用真实浏览器会话进行身份验证；下载显式内容/年龄限制歌曲或 YouTube 强制登录时需要此项。其优先级高于 Web 界面上传的文件，并会使界面中的 Cookie 区域变为只读。详见 [YouTube Cookie](../features/youtube-cookies.md)。 |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(unset)_ | 用于提取 Cookie 的浏览器名称（例如 `chrome`、`firefox`）。容器必须能够访问浏览器 Cookie 存储，因此通常不适用于 Docker。 |

::: tip 通常无需配置这些变量
可以直接在 Web 界面的 **Settings → YouTube cookies** 上传 `cookies.txt`。文件会保存在 `/data` 中（因此容器更新后仍会保留），无需绑定挂载或填写容器路径，并且在 Windows、macOS 和 Linux 上的操作相同。偏好自行管理 Cookie 文件的部署方式仍可继续使用上述变量。
:::

## 示例：配置反机器人验证的 Docker Compose

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_FORCE_IPV4=1
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
    restart: unless-stopped
```

## 获取 cookies.txt

使用浏览器扩展导出 Cookie，例如 Chrome 的 [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) 或 Firefox 的 [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)。登录 Google 账号后，在 `youtube.com` 页面导出，然后通过 **Settings → YouTube cookies** 上传，或按上例将文件挂载到容器中。

完整操作步骤请参阅 [YouTube Cookie](../features/youtube-cookies.md)；如果下载仍失败，请查看[故障排查](../troubleshooting.md)。

::: warning
请妥善保管 `cookies.txt`，不要公开分享。文件包含可访问 Google 账号的会话令牌。
:::
