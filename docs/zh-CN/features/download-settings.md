---
icon: lucide/sliders-horizontal
---

# 下载设置

从侧边栏打开 **Settings**（手机上：**More → Settings**）。设置页分为 General、Audio sources、Downloads & files、Tags & lyrics、Navidrome、Library 和 About 等部分。修改内容会暂存，直到点击底部出现的 **Save changes**；离开页面时若有未保存的修改，系统会先询问。设置会保存到磁盘，容器重启后仍然保留。

## 格式

| 格式 | 扩展名 | 说明 |
|--------|-----------|-------|
| MP3 | `.mp3` | 默认格式，兼容性广。 |
| FLAC | `.flac` | 无损格式；比特率设置不适用。 |
| M4A | `.m4a` | MPEG-4 容器中的 AAC，适用于 Apple 设备。 |
| OGG | `.ogg` | Ogg Vorbis 开放格式，音质和文件大小较均衡。 |
| OPUS | `.opus` | 低比特率下压缩效率最高。 |
| Original | 变化 | 保留可用的最佳音频流，不重新编码。扩展名由源音频决定（例如 `.opus` 或 `.m4a`）。 |

## 比特率

适用于有损格式（MP3、M4A、OGG、OPUS）。FLAC 和 Original 不使用此设置。

| 选项 | Kbps |
|--------|------|
| Low | 128 |
| Medium | 192 |
| High | 256 |
| Best | **320**（默认） |

所有有损格式都会按所选比特率编码。如果 YouTube 提供的音频已经使用目标编解码器且比特率大致相同（例如 **M4A @ 128** 对应约 128 kbps 的 AAC 音频流），Downtify 会直接保留该音频，而不重新编码，因为重新编码只会降低音质。

::: info 提高比特率不会增加音质
YouTube 音频的比特率最高约为 **128–160 kbps**（AAC 或 Opus），Downtify 始终下载可用的最佳音频流。将其编码为 256 或 320 kbps 会生成更大的文件，但只能忠实保留源音频已有的信息，无法恢复源音频中不存在的细节。如果更在意文件大小，请选择较低的比特率。
:::

## 输出文件名模板

默认文件名模板为：

```
{artists} - {title}
```

生成的文件名示例：`The Night Owls - Do I Still Recall.mp3`。

可用占位符：

| 占位符 | 说明 |
|-------|-------------|
| `{title}` | 曲目标题 |
| `{artists}` | 所有署名艺人，使用逗号分隔（例如 `Christina Aguilera, Lil' Kim, Mýa, P!nk`） |
| `{artist}` | 仅第一位署名艺人（例如 `Christina Aguilera`）。艺人名称中原本带有逗号时（如 `Earth, Wind & Fire`），会保留为完整名称。 |
| `{album}` | 专辑名称 |
| `{tracknumber}` | 曲目在专辑中的位置，以两位数字补零（例如 `01`、`12`）。来源没有曲目编号时为空（例如自由文本/YouTube 搜索结果）。 |
| `{year}` | 发行年份（例如 `2025`）。来源没有发行日期时为空（例如自由文本/YouTube 搜索结果）。 |

模板也可以包含 `/` 来创建子文件夹。例如，要将媒体库整理为 `Artist/Album (2025)/01 - Title.mp3`，便于完整下载艺人作品目录时将各专辑及年份放在各自文件夹中，可使用：

```
{artist}/{album} ({year})/{tracknumber} - {title}
```

文件夹占位符建议使用 `{artist}` 而非 `{artists}`：如果使用 `{artists}`，有客串艺人的歌曲会进入以所有艺人命名的独立文件夹（如 `Christina Aguilera, Lil' Kim, Mýa, P!nk/`），而不会归入第一位艺人的目录。

::: info
此设置与 **Organize by artist** / **Organize by album** 开关相互独立。这些开关会将播放列表/专辑下载归入整个媒体库共享的艺人或专辑目录（参见[文件整理](file-organization.md)）。`{tracknumber}` 和 `{year}` 则允许你通过模板逐首手动创建类似目录结构，而无需启用这些开关。
:::

::: tip 合辑
模板对多艺人合辑中的曲目与其他曲目处理方式相同：`{artist}` 使用该曲目自己的第一位艺人，而不是 `Various Artists`。参见[多位艺人与合辑](file-organization.md#several-artists-and-compilations)。
:::

## 并行下载

用于控制同时下载的歌曲数量。可以选择预设值（1、2、3、5、8），也可以在旁边的数字输入框中填写 **1 到 30** 之间的任意数值。

| 数值 | 行为 |
|-------|-----------|
| **1** | 顺序下载，一次一首（最稳妥且资源占用最低） |
| **3** | 默认值，速度和稳定性较为均衡。 |
| **8** | 大型播放列表下载更快。 |
| **最多 30** | 适合高速连接；会使用更多 CPU 和带宽，也更容易触发 YouTube 限流。 |

此限制适用于所有批量下载，包括播放列表/专辑下载、批量队列接口和 CSV [媒体库导入](library-import.md)，也适用于[现有音乐文件夹](external-library.md)的同步查找（歌词、封面、流派）。**不**适用于播放列表监控扫描；监控每次只下载一首新曲目。在设置中更改此值后立即生效，无需重启；服务器会将超出 `1–30` 范围的值限制到有效范围内。

## 下载间隔

每首歌曲下载完成后，Downtify 会等待指定秒数再开始下一首，而不是连续发送请求。

| 数值 | 行为 |
|-------|-----------|
| **0** | 默认关闭，不等待。 |
| **5 / 15 / 30 / 60** | 预设值，也可以填写 **0 到 300 秒**之间的任意数值。 |

此设置适用于播放列表、专辑和批量下载、CSV [媒体库导入](library-import.md)，以及播放列表监控的自动扫描。单首歌曲的手动下载不会等待（没有下一首歌曲需要启动）；批次中的**最后一首**歌曲完成后也不会再等待，避免任务结束后无意义地延迟。

下载大型播放列表或无人值守导入媒体库时，降低**并行下载**数量并设置下载间隔，是避免触发 YouTube 限流的主要方法。

## 同步查找间隔

此设置与下载间隔类似，但适用于[现有音乐文件夹](external-library.md)同步，而非下载任务。同步会按[**并行下载**](#parallel-downloads)设置每批查找一组曲目的歌词、缺失封面和流派，然后等待指定秒数再处理下一批。默认值为 **0**（查找任务会并发运行，但仍受并行下载数限制）。大型收藏可设置几秒间隔，避免同时向 LRCLIB、封面来源和 iTunes 发出过多请求。

## 下载封面

控制 Downtify 是否嵌入专辑封面，默认开启。关闭后将完全跳过封面获取；标题、艺人、专辑、年份和歌词等其他标签仍会正常嵌入。由于无需请求或写入封面图片，文件会更小，下载也略快。

关闭此设置后，**Organize by album** 也不会生成独立的 `cover.jpg`（参见[文件整理](file-organization.md)）。通过这种方式下载的曲目在[播放器](player.md)和媒体库中不会显示封面，而会显示默认的音符图标。

`cover.jpg` 由专辑文件夹中的所有曲目共享。从 Library 页面删除曲目时，也会删除该封面，但只有当它是该文件夹中**最后一首**曲目时才会删除；只要同专辑还有其他曲目，封面就会保留。

## 封面分辨率

只有启用上方的**下载封面**时，此设置才生效。用于指定 Downtify 从 **YouTube Music** 或 **Deezer** 获取并嵌入封面时请求的目标尺寸（宽和高，单位像素）。可选择预设值（300、600、800、1000、1200），也可拖动滑块设置 **300 到 1200** 之间的任意值；当前像素值显示在滑块旁。默认值为 600。

如果要将媒体库用于 Plex 等以较高分辨率显示封面的媒体服务器，此设置会很有帮助。

两个来源的处理方式不同，因为只有一个来源支持按需调整尺寸：

- **YouTube Music**：可以通过修改缩略图 URL 调整尺寸。根据实时 CDN 验证，提高预设值后，大多数专辑封面会返回更多真实细节（而非单纯放大），最高可达源图片本身的分辨率。
- **Deezer**：每首歌曲、专辑、艺人或播放列表的封面只提供四种固定尺寸（56、250、500 和 1000px），无法请求中间尺寸。Downtify 会选择不小于所设尺寸的最小图片。例如请求 300px 时会获取 500px 图片，因为 Deezer 没有 300px 规格；设置超过 1000px 时仍会获取其最大尺寸 1000px。

::: info Spotify 来源的封面不受影响
对于通过 Spotify 解析的曲目/专辑/播放列表，Downtify 已经嵌入 Spotify 公共 embed API 提供的**最大尺寸**封面，没有更大的尺寸可供请求。此设置只会提高通过 YouTube Music 解析的曲目（自由文本搜索、YouTube 链接，以及为获取实际音频而重新匹配 YouTube Music 的 Spotify 曲目）或 Deezer 解析的曲目（粘贴 Deezer 链接或来自[排行榜](charts.md)的曲目）的封面尺寸上限。
:::

更改此设置后立即生效，包括当前打开的搜索页面；无需重新下载磁盘上已有内容。

## 覆盖现有文件

默认开启，与 Downtify 过去的行为一致：每次下载都会完整运行处理流程（获取音频、写入标签、封面和歌词），并覆盖计算得到的输出路径上已有文件。

### “重新下载”具体意味着什么

启用后，重新下载会执行一次**全新的下载流程**，而不是修复已有文件。Downtify 不会检查当前文件，而是按配置顺序搜索[音频来源](#audio-provider)。例如 slskd 排在第一位时，会先尝试 slskd，而不只是将它作为备用来源。Downtify 会获取第一个有响应来源的音频，并写入当前的标签、封面和歌词。

在批量重新下载之前，有一点值得注意：

::: warning 格式不同会留下旧文件
新文件会写入[文件名模板](#output-filename-template)生成的路径，并使用**新**音频的扩展名。只有新旧文件扩展名相同时，Downtify 才会覆盖旧文件。

例如，重新下载 `Artist - Song.mp3` 时，slskd 返回 FLAC，最终会同时保留 `Artist - Song.mp3`（旧文件，不会改动）和 `Artist - Song.flac`。默认启用的 [Leave slskd files in place](slskd-navidrome.md#leave-files-in-place) 会让 slskd 文件留在原处，不复制到下载目录；因此旧文件留在原位置，新文件位于 `slskd/` 下。

文件不会丢失，但会产生重复文件。如需真正替换文件，请参阅[替换音频](replace-audio.md)，该功能会保留原路径、格式和标签。
:::

### 封面来自 Spotify 或 YouTube Music，而非音频文件

无论下载的音频自带什么封面（包括 slskd 文件中嵌入的高分辨率封面），写入标签时都会**丢弃并替换**。Downtify 始终会从 Spotify 或 YouTube Music 获取曲目封面（SoundCloud 链接则使用 SoundCloud 封面），并按你设置的[封面分辨率](#cover-art-resolution)（默认 600px）嵌入。标题、艺人、专辑和其他标签也一样：不会保留来源音频自身的标签。

如果只是想为已有文件添加大尺寸封面，重新下载并不是最佳方法。[升级媒体库](library-upgrade.md)会将每个文件的嵌入封面与 Spotify、iTunes 和 YouTube Music 的版本进行比较，写入最大尺寸的图片，补充缺失歌词和标签，而不会改动音频。

关闭此选项后，磁盘上已有的歌曲不会重复下载。当播放列表、[CSV 媒体库](library-import.md)或[播放列表监控](playlist-monitor.md)中存在相同歌曲时，此设置尤其有用；启用时这些重复歌曲都会重新下载。

关闭后，Downtify 会在下载目录**的任意位置**查找该歌曲，而不只检查新下载将写入的位置，包括：

- 媒体库根目录（单首歌曲下载）；
- 任意播放列表文件夹（播放列表下载、CSV 导入和播放列表监控）；
- 艺人/专辑文件夹，或启用/关闭 **Organize by artist/album** 前使用的平铺目录。

如果音频文件（`.mp3`、`.flac`、`.m4a`、`.ogg`、`.opus`）的名称与[输出文件名模板](#output-filename-template)生成的名称一致（不区分大小写），就会被视为已下载。仅有遗留 `.lrc` 歌词文件不算已下载。如果模板包含目录（如 `{artists}/{title}`），目录也必须一致，以免把其他艺人的同名歌曲误认为当前歌曲。由于文件不包含 Spotify/YouTube 曲目 ID，匹配依赖文件名：重命名过的文件，或使用旧文件名模板保存的文件都无法识别。

跳过歌曲时：

- 不会获取任何内容：音频、封面、歌词都不会下载，也不会重新写入标签。Spotify 曲目会在 YouTube Music 搜索前完成检查，因此已下载歌曲不会消耗搜索请求。
- 队列会将该歌曲显示为已完成；播放列表的 [M3U 文件](m3u-export.md)会指向现有文件所在位置（例如 `../Artist - Title.mp3`），因此播放列表仍可完整播放。
- 同一首歌曲同时加入队列两次时（例如在一个播放列表中重复出现，或出现在两个并行下载的播放列表中），只会下载一份。另一项会等待其完成后跳过。

## 长曲目

**Settings → Downloads → Longest track taken** 会限制下载和串流曲目的时长（默认 **10 分钟**，设置为 `0` 则不限制）。超长歌曲会在获取任何内容前被拒绝，队列显示 *“tracks over … are not downloaded”* 错误，避免将长时间混音和上传视频当作媒体库歌曲处理。同一限制也适用于串流：超长歌曲会返回 `400`（调用方知道时长时会传入 `duration`；否则仍会探测缓存文件），因此长视频不会进入串流缓存。磁盘上已有的文件和通常较长的播客剧集不受影响。

## 音频来源

默认音频来源是 **YouTube Music**。Downtify 使用 [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) 搜索歌曲，并根据曲目时长选择最佳匹配。如果 YouTube Music 没有可接受的匹配，或唯一匹配的时长差距过大（很可能是不同录音），Downtify 会自动回退到普通 YouTube 搜索。详见[工作原理](../how-it-works.md#fallback-to-standard-youtube)。

**Settings → Audio source** 也可设置为仅使用普通 **YouTube**、**SoundCloud**、**slskd**（Soulseek）或 **Deemix**，并按顺序排列备用来源。参见 [slskd 与 Navidrome](slskd-navidrome.md#audio-sources-and-fallback-order)。

### 强制使用指定音频来源

如果 Downtify 选中了错误的 YouTube Music 视频（例如匹配到翻唱而不是原版），可以针对单首歌曲覆盖此选择：

**方式 A：直接粘贴 YouTube Music URL**

将 `https://music.youtube.com/watch?v=…`（或普通 `youtube.com/watch?v=…`）粘贴到搜索栏并点击下载。Downtify 会直接获取该视频中的音频。

::: info
通过 YouTube URL 下载时，元数据（标题、艺人、封面）来自 YouTube，而非 Spotify。若需要准确的标签，请使用方式 B。
:::

**方式 B：为下载失败的歌曲指定音频**

1. 在 **Download Queue** 中，点击失败歌曲下方的 **Force audio source**。
2. 在出现的输入框中粘贴 YouTube 或 YouTube Music URL；启用 **SoundCloud** 来源时，也可以粘贴 SoundCloud 曲目 URL。
3. 按 **Enter** 或点击 **Apply**。

Downtify 会使用指定视频（或 SoundCloud 曲目）重新下载，同时保留 Spotify 的所有元数据（标题、艺人、专辑、封面和歌词）。

## 嵌入的元数据

无论格式为何，Downtify 都会在每个下载文件中嵌入以下标签：

| 标签 | 来源 |
|-----|--------|
| 标题 | Spotify embed |
| 艺人 | Spotify embed |
| 专辑 | Spotify embed。单首歌曲下载时使用 Spotify 公开曲目页显示的专辑名称（曲目 embed 本身不包含专辑信息）。 |
| 年份 | Spotify embed（逐曲目获取） |
| 专辑封面 | Spotify 解析曲目使用 Spotify embed 的曲目封面；其他情况使用 YouTube Music 缩略图或 Deezer 封面。可选，参见[下载封面](#download-cover-art)和[封面分辨率](#cover-art-resolution)。 |
| 歌词 | lrclib（启用时） |
