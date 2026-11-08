---
icon: lucide/file-code
---

# 移动客户端协议

全局服务器暂停功能使用 `GET /api/queue/state`，以及仅限 Web 管理员调用的 `POST /api/queue/pause` / `POST /api/queue/resume`。GET 响应会在现有 `paused`、`state`、`active` 字段基础上增加 `global_pause_supported`、`monitors_paused` 和针对当前请求的 `can_control`。配对设备令牌始终仅限客户端使用，即使所属账户是管理员，也不得向该客户端提供服务器管理操作。手机上的离线副本有独立控制。参见[队列 API](api-reference.md#get-apiqueuestate)。

本协议说明应用（官方 Android 客户端或其他客户端）如何与 Downtify 服务器通信：**发现 → 检查 → 登录（或配对）→ 同步 → 串流 → 上报**。以下内容中的 `api_version` 均为 **1**；各端点完整的请求/响应结构见 [API 参考](api-reference.md#server-and-sign-in)。面向用户的行为（登录、配对、账户、转码限制）见[移动应用](features/mobile-apps.md)和[用户与登录](features/users.md)。

## 1. 发现服务器

使用 mDNS/DNS-SD 浏览 **`_downtify._tcp`** 服务（Android 使用 `NsdManager`）。每个服务包含以下 TXT 记录：

| 键 | 示例 | 含义 |
|-----|---------|---------|
| `id` | `cf12b3c4…` | 服务器 ID（稳定不变；与下文 `server_id` 相同） |
| `name` | `nas` | 服务器名称，可在 Settings → Apps 中编辑 |
| `version` | `3.2.0` | Downtify 版本 |
| `api` | `1` | API 版本 |
| `port` | `8000` | 端口 |
| `scheme` | `http` | `http`（前置反向代理可能提供 `https`，由用户输入该地址） |
| `path` | `/` | 基础路径 |

使用解析得到的主机名和 `port` 构建地址。服务发现仅为便利功能：始终应提供手动输入地址的方式（Docker bridge 网络不会广播服务；详见用户文档）。

## 2. 检查服务器地址

`GET {base}/api/server/info` 是无需凭据的公开接口。

```json
{
  "server_id": "cf12b3c4f530731551690cc62b1365a1",
  "name": "nas",
  "product": "Downtify",
  "version": "3.2.0",
  "api_version": 1,
  "require_sign_in": true,
  "capabilities": {
    "transcoding": { "available": true, "formats": ["aac", "mp3", "opus"], "bitrates": [96, 128, 160, 192, 256, 320] },
    "signed_urls": true, "pairing": true, "password_sign_in": true, "podcasts": true, "discover": true, "lyrics": true, "library_sync": true
  }
}
```

- 如果 `product` 不是 `Downtify`，或 `api_version` 高于客户端支持版本，则拒绝继续。
- 保存 `server_id`：即使地址发生变化，它仍可用于识别服务器。若之后该地址返回了不同 ID，则说明连接的是另一台服务器。
- 根据 `capabilities` 启用相应功能（例如，若 `transcoding.available` 为 `false`，则隐藏移动网络音质选项）。
- `capabilities.password_sign_in` 决定下一步如何向用户索取凭据：值为 `true` 时询问用户名和密码，否则请求配对码（账户功能已关闭、本地密码登录被禁用，或服务器早于 `POST /api/auth/token`）。

## 3. 登录或配对

无论采用哪种方式，最终都会获得绑定到某个用户的相同设备令牌。通常使用登录；如果手机不应接触密码，或网页已经打开，则可使用配对快捷完成。

### 登录

用户输入其网页登录使用的用户名和密码：

```http
POST /api/auth/token
Content-Type: application/json

{ "username": "maria", "password": "…", "device_name": "Pixel 8", "platform": "android" }
```

响应结构与下文配对响应相同（包含 `token`、`device`、`server`、`user`）。错误码：`401` 用户名或密码错误；`429` 尝试次数过多（等待 `Retry-After` 秒；与网页登录共享限制）；`409` 账户功能已关闭，此时应提供配对选项。不要保存密码；从此以后使用令牌作为凭据。

### 配对

用户在网页打开 **Settings → Apps → Pair a phone**，页面会显示二维码和 8 位配对码。

- **二维码内容：** `downtify://pair?url=<base URL>&sid=<server_id>&code=<code>`。使用 `url` 作为基础地址（这是用户浏览器实际使用的地址；如果同时有发现到的地址，应优先使用它），并将 `sid` 与 `/api/server/info` 的结果比对。
- **手动输入配对码：** `XXXX-XXXX`；按用户输入原样发送（服务器会规范化大小写、空格和连字符）。

```http
POST /api/auth/pair
Content-Type: application/json

{ "code": "K7QM-2XPD", "device_name": "Pixel 8", "platform": "android" }
```

```json
{
  "token": "dtfy_8uz4d35zjpn2_<secret>",
  "device": { "id": "8uz4d35zjpn2", "name": "Pixel 8" },
  "server": { "server_id": "cf12b3c4…", "name": "nas" },
  "user": { "username": "maria", "role": "user" }
}
```

- `401` 配对码错误、过期或已使用；`429` 尝试次数过多（需等待 `Retry-After` 秒）。

### 保管令牌

- 将令牌保存在由 Android Keystore 保护的存储中（EncryptedSharedPreferences / Jetpack DataStore + Tink）；令牌只显示一次，之后无法再次获取。
- **每个**请求都通过 `Authorization: Bearer <token>` 发送令牌。只有关闭账户功能（`DOWNTIFY_DISABLE_AUTH`）或较旧的服务器才会令 `require_sign_in` 为 `false`；仍应发送令牌，以便服务器告知客户端设备是否已取消配对。
- 设备归登录或出示配对码的用户所有（响应中的 `user`：`{ "username", "role" }`）；`GET /api/me` 可返回该用户身份。应在应用中显示该信息（例如“登录身份：maria”）。
- 使用令牌调用 `GET /api/auth/status` 会返回 `{ "signed_in": true, "via": "device", "user": { "username", "role", … }, "device": { "id", "name" }, … }`，可低成本检查设备是否仍处于配对状态。

**取消配对/撤销：** 任意请求会返回 `401` 和 `{"detail": "Invalid or revoked token"}`，WebSocket 会以代码 `4401` 关闭。应丢弃令牌并引导用户重新登录。

**设备可以执行的操作：** 下文列出的所有操作，以及 Web API 的读取接口、搜索和预览（`/api/songs/search`、`/api/url/resolve`、`/api/preview`）、购买歌曲以支持艺人（`/api/buy`，参见[支持艺人](features/support-artists.md)）、请求服务器下载（`POST /api/download/url|batch|album`）、喜欢歌曲、记录收听和播放/下载播客剧集。设备调用 Settings、凭据管理、删除文件和设备管理接口时会收到 `403`。搜索、预览、串流和请求服务器下载属于共享功能：任何人下载的曲目都可播放，之后也可通过下载将它纳入自己的条目。媒体库消息流、播放列表、喜欢记录和队列包含配对账户自己的条目（管理员设备可查看全部）。账户被删除或账户所有者选择 **Sign out everywhere** 后，设备会取消配对（返回 `401`）。

## 4. 同步媒体库

```http
GET /api/v1/library?since=<cursor>
```

```json
{
  "cursor": 1742,
  "full": false,
  "tracks": [
    {
      "id": "t7b255c87668ba03b",
      "file": "Portishead - Roads.flac",
      "title": "Roads", "artist": "Portishead", "artists": ["Portishead"],
      "album": "Dummy", "album_artist": "Portishead",
      "album_id": "6aa1df0c3e5f2b11", "artist_id": "0a92c1e0bb3d8f44",
      "track_number": 3, "year": "1994", "duration": 305.12,
      "codec": "flac", "bitrate": 912000, "sample_rate": 44100, "channels": 2,
      "size": 34812211, "added": 1789600669, "has_cover": true, "explicit": true, "playlists": ["Trip-hop"]
    }
  ],
  "deleted": ["t0c4…"]
}
```

- 首次启动：传入 `since=0`，返回 `full: true`，`tracks` 为整个媒体库。
- 后续请求：传入 `since=<last cursor>`，只返回此游标之后新增或更改的曲目，以及已删除曲目的 ID。只有应用完响应后才保存 `cursor`。
- 任何时候若返回 **`full: true`**（游标过期；服务器只保留 90 天内已删除曲目的记录，或服务器不识别该游标），都应使用 `tracks` 替换本地媒体库。
- **`id`** 在文件移动和重命名后保持稳定（具体规则见 `downtify/library_sync.py`）；如果文件在同一次扫描中既移动又更改标签，它会以新 ID 返回，同时旧 ID 会列入已删除项。所有本地数据（离线文件、喜欢记录、队列、历史）都应以 `id` 为键，不能使用 `file`。
- **`explicit`**：显式内容曲目的字段值为 `true`，其他曲目不包含该字段；缺失时按 `false` 处理。应像 Web 应用一样在标题旁显示小小的“E”（参见[显式内容标记](features/explicit-marker.md)）。
- **分组：** 专辑按 `album_id` 分组（艺人名 + 专辑名，不区分大小写；`""` 表示无专辑），艺人按 `artist_id` 分组（专辑艺人）。这与 Web 应用的分组方式完全一致。
- 支持 `ETag`/`If-None-Match`（对于同一 `since` 没有变化时返回 `304`）。
- `refresh=true` 会立即重新扫描文件夹（用于下拉刷新）；否则列表背后的扫描结果会缓存约一分钟。
- 服务器通过 WebSocket `library_changed`（见下文）通知媒体库发生更改时，应再次同步。
- **用户可见的媒体库：** 媒体库为共享内容，因此消息流包含所有曲目，但管理员[对用户隐藏](features/users.md#hiding-from-users)的曲目除外（管理员设备可获取全部曲目）。曲目被隐藏时会作为已删除 ID 返回；重新显示时会作为普通行返回。其他字段结构不会因此改变。播客节目、剧集进度、收听记录和屏蔽列表同样按账户隔离；订阅节目需从网页操作。

以下读取接口都按曲目 ID 查询：

| 端点 | 返回内容 |
|----------|---------|
| `GET /api/v1/tracks/{id}` | 单条曲目记录 |
| `GET /api/v1/tracks/{id}/lyrics` | `{ "synced": "<LRC>", "plain": "…" }`（任一字段可能为空） |
| `GET /api/v1/tracks/{id}/loudness` | 曲目的[播放响度配置](features/playback-normalization.md)：`{ "state", "gain_db", "integrated_lufs", "true_peak_dbtp", "algorithm_version", "fingerprint", "source_etag", "source_size" }`。仅当 `state` 为 `ready` 且 `algorithm_version` 为 `1` 时应用 `gain_db`；上限为 +12 dB，且不得超过 `-1 - true_peak_dbtp`。其他情况（`unanalysed`、`silent`、旧服务器返回 `404`）均使用原始音量。`source_etag` 和 `source_size` 是原文件串流的 `ETag` 和大小；只有它们与下载文件匹配时，才将配置绑定到离线副本。 |
| `GET /api/v1/tracks/{id}/cover?size=150\|300\|600` | JPEG 缩略图；省略 `size` 可获取完整图片。带有 `ETag` 和 `Cache-Control: private, max-age=604800`。 |
| `GET /api/v1/playlists` | `[{ "name", "liked", "manual", "count", "cover", "track_ids": [...], "owner", "visibility", "mine", "followed", "can_edit_tracks", "shared_with_me", "new", "hidden_count" }]`（`cover` 是供 `GET /playlist-cover?file=` 使用的路径，或为空字符串）。`track_ids` 按播放列表顺序排列，同一 id 可能出现多次：`manual` 播放列表可以[重复同一首歌曲](features/playlist-order.md)，因此列表行应同时以位置和 id 作为键。其中也包含他人共享或你关注的播放列表（`mine: false`）：应与用户自己的列表分开呈现，并标明 `owner`。除非 `can_edit_tracks` 表明用户是该列表的[编辑者](features/collaborative-playlists.md)，否则为只读；编辑者只能修改歌曲，不能重命名、共享或删除列表。用户自己的列表还包含 `shared_with` 和 `editors`。 |
| `GET /api/v1/usernames` | `{ "enabled", "usernames": [...] }`，表示可与其共享播放列表的用户。 |
| `POST` / `DELETE` `/api/v1/playlists/follow` | 请求体（或 `?name=`）为 `{ "name" }`；关注或取消关注公开播放列表。 |
| `POST /api/v1/playlists/seen` | 请求体 `{ "name" }`；清除共享给用户的播放列表上的 `new` 标记。 |
| `GET /api/v1/playlists/hidden?name=` | `{ "name", "songs": [{ "key", "label", "track_id", "hidden_at" }] }`，即用户从自己导入的播放列表中隐藏的歌曲（文件消失后 `track_id` 为空字符串）。 |
| `POST /api/v1/playlists/hidden` | 请求体 `{ "name", "hide": [track_ids], "show": [keys] }`；从用户导入的播放列表中隐藏曲目（监控或重新导入链接时仍保持隐藏，但曲目仍在媒体库中），或重新显示隐藏曲目。返回 `{ "name", "hidden", "keys", "shown", "restored", "count", "track_ids" }`；将 `keys` 作为 `show` 发送即可撤销隐藏。应在 `mine` 为真的、且 `manual` 和 `liked` 均为假的播放列表中提供此功能（否则返回 `409`）。参见[隐藏播放列表歌曲](features/hidden-playlist-songs.md)。 |
| `GET /api/v1/likes` | `{ "track_ids": [...] }`，按最新时间在前排序。 |
| `PUT /api/v1/likes` | 请求体 `{ "track_id", "liked" }`；操作具有幂等性。 |

## 5. 串流和下载

```http
GET /api/v1/tracks/{id}/stream                          # 原始文件
GET /api/v1/tracks/{id}/stream?format=opus&bitrate=160  # 转码文件（opus | aac | mp3；96–320）
```

- 完整支持 **HTTP Range**（`206`、`Content-Range`、`Accept-Ranges: bytes`），并返回准确的 `Content-Length`、`Content-Type`（`audio/flac`、`audio/mpeg`、`audio/mp4`、`audio/ogg`）。也支持 `HEAD`。
- 转码副本返回 `X-Downtify-Transcoded: opus/160`；如果原文件已满足要求（有损格式且比特率未超过请求值），则返回 `no`。
- 首次请求时会创建转码副本（请求会等待；一首歌可能需要数秒），并缓存结果；之后会像普通文件一样提供。转码请求应设置较长的读取超时（≥ 60 秒）。
- **离线副本：** 使用相同 URL，并添加 `download=true` 获取 `Content-Disposition` 文件名。使用 `Range` 恢复中断的下载。规划存储空间时，可使用 `Content-Length` 中的大小（原始文件也可使用曲目的 `size`）。
- Media3：在 `DataSource.Factory` 中设置 `Authorization` 标头（`DefaultHttpDataSource.Factory().setDefaultRequestProperties(...)`）；使用 `CacheDataSource` 进行缓存。

## 6. 签名 URL（用于 Cast 和不支持请求标头的播放器）

Cast 接收端会自行获取媒体，无法发送令牌。可向服务器申请签名 URL：

```http
POST /api/v1/sign
Authorization: Bearer <token>

{ "items": [ { "path": "/api/v1/tracks/t7b2…/stream", "params": { "format": "aac", "bitrate": "256" } },
             { "path": "/api/v1/tracks/t7b2…/cover", "params": { "size": "600" } } ],
  "ttl": 3600 }
```

```json
{ "urls": ["/api/v1/tracks/t7b2…/stream?format=aac&bitrate=256&exp=1790479684&kid=8uz4d35zjpn2&sig=…", "…"],
  "expires_at": 1790479684 }
```

- 在 URL 前加上基础地址。设备保持配对期间，在 `exp` 到期前，仅对完全匹配的路径和参数允许执行 `GET`/`HEAD`。`ttl` 范围为 60 秒至 24 小时。
- 可签名路径：`/api/v1/tracks/…`、`/downloads/…`、`/media/…`、`/cover`、`/playlist-cover`。
- CORS：响应允许任意来源，并公开 `Accept-Ranges`、`Content-Length`、`Content-Range`、`ETag`、`X-Downtify-Transcoded`。
- 接收端必须能够访问服务器地址（处于同一网络，或使用公开 HTTPS 地址）。

## 7. 实时更新（WebSocket）

使用 `WS {base}/api/ws?client_id=<uuid>`，并在握手时设置 `Authorization` 标头（OkHttp 支持）。无法发送该标头的客户端，可通过 `POST /api/auth/ws-ticket` 获取一次性、有效期 60 秒的票据，然后使用 `&ticket=<ticket>` 连接。

客户端可以依赖以下消息：

| 消息 | 触发时机 |
|---------|------|
| `{ "type": "library_changed" }` | 曲目新增、移除或移动（约延迟 2 秒合并通知）；应重新同步。 |
| `{ "type": "playlists_changed" }` | 播放列表共享、取消共享、关注、复制、分离、重命名或删除，或其中的歌曲被隐藏/重新显示；重新获取 `GET /api/v1/playlists`。 |
| `{ "type": "likes", "count": 3 }` | 任一位置的喜欢记录更改；重新获取 `GET /api/v1/likes`。 |
| `{ "type": "queue_reload" }` | 一次性加入大量下载任务；重新获取 `GET /api/queue`。 |
| `{ "song": {…}, "progress": 42.5, "status": "downloading"\|"done"\|"error", "message", "filename", "provider" }` | 服务器下载进度（没有 `type`）；仅推送当前用户自己的任务（管理员设备可查看所有任务）。 |
| `{ "type": "podcasts" }` / `{ "type": "podcast_progress", … }` | 播客剧集下载或进度更新。 |
| `{ "type": "device_paired", … }` | 新设备已配对（此消息供网页使用；客户端可忽略）。 |

“服务器正在下载 N 首歌曲”：调用 `GET /api/queue`，统计 `status` 为 `queued` 或 `downloading` 的行数，并根据进度消息更新。等待中的行包含 `position`（队列中的 1 起始位置；完成后为 `null`）和 `user_ids`（所有等待该任务的账户；多个账户同时请求同一曲目时，共享一个任务行）。关闭代码 `4401` 表示已取消配对。

## 8. 上报播放

```http
POST /api/discover/listens

{ "track_id": "t7b2…", "play_id": "<uuid per play>", "played_at": "2026-09-27T10:00:00Z" }
```

- 每次播放上报一次，在曲目播放过半（或已播放 4 分钟）后上报，与 Web 播放器的规则一致。
- `play_id` 使重试安全（同一次播放只计一次）；`played_at` 允许应用之后上报离线时的播放记录（未来时间会按当前时间处理）。离线时先将记录加入队列，恢复联网后发送。

**当前正在播放的内容**（管理员 Activity 页面中显示，类似 Jellyfin 控制面板）与收听次数统计相互独立：

```http
POST /api/activity/playback

{ "player": "<install id>", "state": "playing", "track": { "track_id": "t7b2…", "title": "Roads", "artist": "Portishead", "album": "Dummy", "duration": 305 }, "position": 42 }
```

- 在歌曲开始、暂停/恢复（`state: "paused"`/`"playing"`）、停止时（`"stopped"`，`track` 可为 `{}`）发送；播放期间约每 30 秒发送一次。仅在线时发送，不要将这些消息排队。
- `player` 可为此安装实例中任意稳定 ID。应用在服务器中会以设备名称显示。

播客剧集使用 `PUT /api/podcasts/episodes/{id}/playback` 并发送 `{ "position_seconds", "played" }`（参见 API 参考），播放期间约每 10 秒发送一次，暂停时也发送。

## 错误处理摘要

| 状态码 | 含义 |
|--------|---------|
| `401` | 凭据缺失、无效或已撤销；重新配对（或登录）。 |
| `403` | 已登录，但该操作需要在网页上由管理员执行。 |
| `404` | 未知曲目 ID 或文件缺失；重新同步。 |
| `429` | 请求受限（配对）；等待 `Retry-After` 秒。 |
| `499` | 客户端断开连接后服务器停止转码（通常不会遇到）。 |
| `501` | 请求转码但服务器没有 ffmpeg；使用 `format=original`。 |

## 仅媒体库策略

`GET /api/server/info` 可选包含布尔值 `library_only`（默认 `false`）。当前客户端应按配对服务器记住该值，并在收到 `music_policy_changed` 后刷新服务器信息。值为 `true` 时，使用媒体库搜索和本地文件标识，隐藏外部搜索结果、预览、预取和串流，并移除仅串流队列项。服务器会对外部音乐端点返回 HTTP `409`。参见[仅媒体库模式](features/library-only.md)。

## 音乐回收站（管理员）

启用[音乐回收站](features/music-trash.md)后，管理员设备可以将歌曲移入回收站、恢复歌曲，并重新下载已过期的歌曲；所用端点与 Web 应用相同，均位于 `/api/v1/library/trash` 下（参见 [API 参考中的音乐回收站](api-reference.md#music-trash)）：

- 每次配对时调用 `GET /api/v1/library/trash/capabilities`；账户可能发生变化时也应重新查询。只有 `can_manage` 为 `true` 时才显示回收站；返回 `404`（旧版服务器）或任何错误均视为功能关闭。服务器会重新校验每个请求：若返回 `403`（`admin_required`），说明账户不再是管理员，应隐藏回收站。
- 移动操作分三步：使用 `{ "track_ids": [...] }`（媒体库 ID，最多 200 个）调用 `POST …/preview`；之后每秒左右轮询 `GET …/preview/{request_id}`，直到 `state` 为 `ready`；向用户展示 `items`（标题、格式、路径）并请求确认，随后使用其中的 `confirmation` 调用 `POST …/confirm`（有效期 10 分钟）。确认响应先于实际移动操作返回，因此歌曲应显示为等待处理，而不是已删除。
- 确认移入回收站的歌曲会以已删除 ID 的形式从媒体库消息流移除（出现在 `GET /api/v1/library` 的 `deleted` 中）；恢复的歌曲会以**相同的 `id`** 返回，因此以 ID 为键的喜欢记录、播放列表、队列条目和离线文件仍能关联到该歌曲。在本次会话首次成功同步之前，不要删除用户队列或离线文件；只有同步明确确认 ID 消失时才视为已移除。
- 对 `409` 响应中的 `detail.code` 显示相应提示（代码列表见 API 参考）；未知代码按“操作未完成，未删除任何内容”处理。
