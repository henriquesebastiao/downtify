---
icon: lucide/cog
---

# 工作原理

Downtify 的下载流程分为三个阶段：

```
Spotify embed  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
  （元数据）          （匹配音频）            （下载并写入标签）
```

## 1. 元数据：抓取 Spotify embed

粘贴 Spotify URL 后，Downtify 会获取该歌曲、专辑或播放列表对应的公开 `open.spotify.com/embed` 页面。无需 Spotify 账号、API 密钥或 Premium 订阅，因为 embed 页面可公开访问。

对于**歌曲**，embed 会返回标题、艺人、专辑名称、发行年份、时长和封面图片 URL。

对于**专辑和播放列表**，embed 会返回曲目列表。播放列表 embed 通常最多包含约 50–100 首歌曲，因此对于包含数百首歌曲的播放列表，Downtify 还会通过 Spotify 匿名 `api.spotify.com` 接口分页请求完整列表。

::: info 逐曲目补充元数据
播放列表 embed 条目缺少发行年份，并且使用播放列表封面，而不是每首曲目自己的专辑封面。对于[播放列表监控](features/playlist-monitor.md)，Downtify 会在下载前逐首重新获取新曲目信息，以便取得正确封面和年份。
:::

## 2. 音频匹配：先搜索 YouTube Music，再搜索 YouTube

Downtify 使用 [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) 在 YouTube Music 上搜索最佳音频匹配项。搜索词由曲目标题和艺人名称组成。

只有标题与来源曲目相似，且至少有一位艺人相同的结果才会被接受。Spotify 使用短横线表示版本的后缀、YouTube Music 使用括号表示版本的后缀时，会视为同一版本（`Tubarões - Ao Vivo` 可匹配 `Tubarões (Ao Vivo)`）。YouTube Music 合并在一个条目中的艺人署名（如 `A, B, and C`）会先拆分再比较。艺人名称开头的 “The” 会忽略（`Eden Project` 可匹配 `The Eden Project`）。上传标题中由 ` - ` 分隔的部分也可与曲目标题匹配（如 `くちづけDiamond - Kuchizuke Diamond`、`Game OST - Song Title - Artist`），但其他部分不能指向不同版本。除非来源曲目本身就是相应版本，否则会排除卡拉 OK、翻唱、纯音乐、加速/减速、现场（包括 `Ao Vivo` / `En Vivo`）、原声、混音和其他语言版本（如 `(Spanish Version)`）。在其余结果中，优先选择时长最接近 Spotify 版本的结果；专辑名称相同也会获得加权。如果没有符合条件的结果，系统会调换搜索词顺序（从 `<artist> <title>` 改为 `<title> <artist>`）再次搜索。YouTube Music 会根据词序对结果排序，有些歌曲只有按某一种顺序搜索时才会出现在前列。如果仍未找到结果且已知专辑，系统会直接扫描该专辑的曲目列表。

### 回退到普通 YouTube

有些歌曲未收录在 YouTube Music 中，或只有其他录音版本。因此在以下情况下也会搜索普通 YouTube：

- YouTube Music **没有可接受的匹配项**；或
- 最佳匹配的时长与 Spotify 版本相差**超过 10 秒**，这通常意味着是不同录音（例如同名配音版本）。

普通 YouTube 的结果也会经过相同的标题、艺人和版本检查，且时长与 Spotify 版本相差不得超过 30 秒。只有在 YouTube 结果的时长严格更接近时，才会替换较弱的 YouTube Music 匹配项；否则保留 YouTube Music 结果，因为其曲库上传通常音质更好。

如果两个站点都没有可接受的匹配项，该曲目会以 `Could not find a YouTube match for '<title>'` 错误结束，而不会下载错误歌曲。

直接输入 YouTube URL 时会跳过此步骤，Downtify 会下载指定视频。

**SoundCloud** 也是一种可选音频来源（位于 Settings → Audio sources，默认关闭）：轮到该来源时会按自己的标题、艺人和时长规则搜索 SoundCloud；如果粘贴的是 SoundCloud 曲目链接（标题、艺人和封面均来自 SoundCloud），则直接下载指定曲目。详情请参阅 Features 下的 SoundCloud 页面。

::: info Deezer 链接
粘贴 Deezer 歌曲/专辑/播放列表/艺人链接（`deezer.com/track/…`）时，处理方式与 Spotify 链接相同：通过 Deezer 公共 REST API 获取标题、艺人、专辑和封面；下载前，每首曲目都可以从 YouTube 完整串流试听；之后使用本步骤在 YouTube Music/YouTube 上匹配。除 Deezer API 本身返回的内容外，Downtify 不会自行解析 Deezer 艺人唱片目录。因此 Deezer 链接可以下载内容，播放列表也会生成自己的 M3U 和封面，但无法由[播放列表监控](features/playlist-monitor.md)监控。
:::

## 3. 下载并写入标签：yt-dlp + ffmpeg + mutagen

### 下载

[yt-dlp](https://github.com/yt-dlp/yt-dlp) 从 YouTube 下载音频（SoundCloud 曲目则从 SoundCloud 下载）。对于 YouTube，Downtify 会按顺序尝试多个播放器客户端（`ios`、`android`、`web_embedded`、`mweb`、`web`、`tv`），以应对 YouTube 的机器人检测验证。高级反机器人选项请参阅[环境变量](getting-started/environment-variables.md)。

### 转换

[ffmpeg](https://ffmpeg.org/) 会将原始音频转换为所选格式（MP3、FLAC、M4A、OGG 或 OPUS）和比特率。

### 写入标签

[mutagen](https://mutagen.readthedocs.io/) 会将元数据写入转换后的文件：

| 标签 | 是否写入 |
|-----|---------|
| 标题 | 是 |
| 艺人 | 是，写入所有署名艺人；`ARTISTS` 标签中也会为每位艺人分别写入一个值 |
| 专辑艺人 | 是，优先使用来源为专辑标注的艺人，否则使用第一位艺人 |
| 合辑标志 | 仅当来源将专辑署名为 “Various Artists”，或管理员将其标记为合辑时写入 |
| 专辑 | 是 |
| 年份 | 是 |
| 专辑封面（JPEG） | 是 |
| 歌词（普通和同步） | lrclib 返回结果时写入 |
| 显式内容标记 | 歌曲被标记为显式内容时写入（参见[显式内容标记](features/explicit-marker.md)） |

具体使用的 ID3/Vorbis/MP4 标签取决于输出格式。歌词嵌入方式详见[歌词](features/lyrics.md)。

## 实时进度

Downtify 通过 **WebSocket** 连接（`/api/ws`）将下载进度实时推送到浏览器。yt-dlp 报告进度时，服务器会向所有已连接客户端广播百分比和状态更新，因此进度条会即时变化，无需轮询或重新加载页面。

## 文件命名和整理

输出文件名根据 Settings 中配置的模板生成（默认值为 `{artists} - {title}`）。文件名中不允许使用的字符会被移除。

启用 *Organize by artist* 后，文件会放入以专辑艺人命名的子文件夹；如果是多艺人合辑中的曲目，则使用该曲目的第一位艺人。否则，单曲会放在下载目录根目录，播放列表/专辑曲目会放在各自的子文件夹中。参见[多位艺人与合辑](features/file-organization.md#several-artists-and-compilations)。
