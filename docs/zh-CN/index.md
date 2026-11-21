---
layout: home
title: Downtify
titleTemplate: "自托管的 Spotify 下载器与音乐播放器"
description: "内置播放器的自托管 Spotify 下载器。粘贴 Spotify、YouTube Music、Deezer 或 SoundCloud 链接，即可获得带完整标签的 MP3 或 FLAC 文件，无需 API 密钥。"
icon: lucide/house
hero:
  eyebrow: 自托管音乐下载器
  headline:
    - 粘贴链接，
    - 音乐到手。
  lead: 内置播放器的自托管音乐下载器。粘贴 Spotify、YouTube Music、Deezer 或 SoundCloud 链接，即可获得标签完整的音乐库，随时在浏览器、手机或媒体服务器中播放。
  note: 无需 Spotify 账号、API 密钥或 Premium。
  actions:
    - text: 快速入门
      link: /zh-CN/getting-started/installation/
      primary: true
    - text: 在 GitHub 上查看源码
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: 发行版本
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker 拉取量
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: GitHub 星标
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: 许可证
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: '44 秒了解 Downtify：粘贴播放列表链接，一键下载，保持同步，并在电脑和手机上配合同步歌词播放。'
why:
  - icon: link
    title: 一个链接就够了
    text: 粘贴来自 Spotify、YouTube Music、Deezer 或 SoundCloud 的歌曲、专辑、整个播放列表或艺人，或者直接输入你想听的内容。Downtify 会找到音频并全部带回家。
    link: /zh-CN/how-it-works/
  - icon: tag
    title: 值得珍藏的文件
    text: 每个文件都带有封面、所有署名艺人、专辑、年份、曲目编号和歌词（有同步歌词时为同步歌词）。可选 MP3、FLAC、M4A、OGG 或 Opus，也可保留来源音频原样。
    link: /zh-CN/features/download-settings/
  - icon: music
    title: 你自己的流媒体服务
    text: 浏览器中的完整播放器，支持同步歌词、卡拉OK、播放队列、已点赞歌曲、播放列表和播客。Android 和 iOS 应用让你随身携带音乐库，离线也能听。
    link: /zh-CN/features/player/
  - icon: radar
    title: 设置一次，无需操心
    text: 监控播放列表和艺人。新歌和新发行会按你选择的频率自动下载。
    link: /zh-CN/features/playlist-monitor/
  - icon: server
    title: 为家庭服务器打造
    text: 同时支持 amd64 和 arm64 的单个 Docker 镜像，SQLite 或 PostgreSQL，带可选单点登录的家庭成员账号，以及 Jellyfin、Navidrome 和 Plex 能识别的播放列表。
    link: /zh-CN/getting-started/
  - icon: shield
    title: 没有附加条件
    text: 无需 Spotify API 密钥、开发者账号或 Premium。应用没有广告、没有使用统计，也没有任何付费内容。它是自由开源软件。
    link: /zh-CN/contributing/
showcase:
  - shot: now-playing
    label: 正在播放
    caption: 歌词逐行跟随歌曲，旁边是封面和接下来的歌曲。
    alt: 全屏的正在播放界面，包含专辑封面、高亮当前行的同步歌词和播放队列。
  - shot: karaoke
    label: 卡拉OK
    caption: 大号歌词随演唱逐行填色，可在第二块屏幕上打开。
    alt: 卡拉OK 界面，大号歌词在封面配色的动态背景上逐行填色。
  - shot: home
    label: 首页
    caption: 粘贴链接或搜索新内容，从上次停下的地方继续。
    alt: 首页，包含用于粘贴链接或搜索的输入框、音乐库统计、正在播放的专辑和最近添加的专辑。
  - shot: library
    label: 音乐库
    caption: 专辑、艺人、播放列表和曲目，按你的方式排序和筛选。
    alt: 音乐库页面，包含专辑封面网格以及专辑、艺人、播放列表和曲目标签页。
  - shot: playlist
    label: 播放列表
    caption: 你自己的播放列表，有专属封面，可播放、分享或下载为 ZIP。
    alt: 播放列表页面，包含封面、按钮，以及带专辑、格式和发行日期的歌曲列表。
  - shot: phones
    label: 在手机上
    caption: 同一个应用也能在手机上使用，可从浏览器安装。
    alt: 三部手机上的 Downtify，分别显示首页、正在播放和音乐库。
pipeline:
  - icon: link
    title: 粘贴链接
    text: Spotify、YouTube Music、Deezer 或 SoundCloud，也可以直接输入歌名。
  - icon: search
    title: 查找音频
    text: 在 YouTube Music 上找到最接近的结果，并用时长核对。也可按需启用其他音源。
  - icon: download
    title: 下载并写入标签
    text: 由 yt-dlp 和 ffmpeg 获取音频，封面、歌词和标签写入文件。
  - icon: music
    title: 随处播放
    text: 在浏览器、手机，或 Jellyfin、Navidrome 和 Plex 中播放。
quickStart:
  - text: 安装指南
    link: /zh-CN/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /zh-CN/getting-started/docker-compose/
  - text: 一键安装
    link: /zh-CN/getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify Android 版
    text: 官方应用。可在网络中找到你的服务器，Wi-Fi 下以原始音质串流，移动数据下使用较小音质，支持离线保存歌曲和 Android Auto。仍在测试中，可从 GitHub Releases 和 Obtainium 获取。
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify iOS 版
    text: 由社区成员为 iPhone 和 iPad（iOS 17 或更高版本）开发，支持离线歌曲和锁屏控制。公开测试版在 TestFlight 上。
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: 在 GitHub 上加星
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: 赞助
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: 参与翻译
    link: /zh-CN/features/internationalization/
    icon: languages
  - text: 参与贡献
    link: /zh-CN/contributing/
    icon: git-pull-request
---

## 为什么选择 Downtify

<HomeHighlights :items="$frontmatter.why" />

## 近距离看看

<HomeShowcase :items="$frontmatter.showcase" />

## 工作原理

Downtify 不需要 Spotify API 密钥，也从不从 Spotify 下载任何内容。它从公开来源读取链接指向的内容，选择时长最匹配的 YouTube Music 音频，用 `yt-dlp` 下载、用 `ffmpeg` 转换、用 `mutagen` 写入标签，全部在一个 Docker 容器中完成。没有合适结果时由 YouTube 补上，SoundCloud、Soulseek 和 Deemix 在你开启后也会参与。[查看每一步的详细说明](how-it-works.md)。

<HomePipeline :steps="$frontmatter.pipeline" />

## 可以粘贴什么

| 来源          | 支持内容                       | 示例                                |
| ------------- | ------------------------------ | ----------------------------------- |
| Spotify       | 歌曲、专辑、播放列表、艺人     | `open.spotify.com/playlist/…`       |
| YouTube Music | 歌曲、专辑、播放列表、艺人     | `music.youtube.com/playlist?list=…` |
| YouTube       | 视频                           | `youtube.com/watch?v=…`             |
| Deezer        | 歌曲、专辑、播放列表、艺人     | `deezer.com/album/…`                |
| SoundCloud    | 歌曲                           | `soundcloud.com/artist/track`       |
| 搜索          | 任何你想输入的内容             | `The Night Owls Do I Still Recall`  |
| CSV           | 媒体库导出文件                 | Soundiiz, TuneMyMusic, Exportify    |

## 它能做的一切

每个功能都有自己的页面，详细说明每个选项。[一览全部功能](features/index.md)。

<HomeFeatures />

## 一分钟即可运行

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

打开 [`localhost:8000`](http://localhost:8000)，以 **admin** 账号和 **downtify** 密码登录，然后粘贴链接。请立即在 **设置 → 常规** 中修改这个密码。音乐会连同标签一起保存到 `/path/to/music`。

<HomeActions :actions="$frontmatter.quickStart" />

## 常见问题

::: details 需要 Spotify 账号、Premium 或 API 密钥吗？
不需要。Downtify 从 Spotify 的公开嵌入（embed）页面读取歌曲、专辑和播放列表信息，因此不需要任何凭据，音频也从不来自 Spotify。参见[工作原理](how-it-works.md)。
:::

::: details 音频从哪里来，质量如何？
默认来自 YouTube Music：选择时长与歌曲最匹配的结果，YouTube 作为备选。可以按需选择 MP3、FLAC、M4A、OGG 或 Opus 及比特率，也可以不重新编码、直接保留来源的最佳音频。无损文件来自你自己添加的音源：保留原始格式的自建 [Soulseek（slskd）](features/slskd-navidrome.md) 服务器，或 [Deemix](features/deemix.md) 服务器。参见[下载设置](features/download-settings.md)。
:::

::: details 能配合 Jellyfin、Navidrome 或 Plex 使用吗？
可以。文件按媒体服务器期望的方式写入标签，存放在 `艺人/专辑/` 目录中，每个播放列表都会生成它们能识别的标准 M3U 文件。Navidrome 还可以同步播放列表，并根据 Deezer 设置评分。参见[文件整理](features/file-organization.md)和[导出 M3U](features/m3u-export.md)。
:::

::: details 能在树莓派或 NAS 上运行吗？
镜像同时提供 `amd64` 和 `arm64` 版本，Umbrel、CasaOS 和 HomeDock OS 都能一键安装。参见[一键安装](getting-started/one-click.md)。
:::

::: details YouTube 提示 "Sign in to confirm you're not a bot"，怎么办？
在 **设置 → YouTube Cookie** 中上传 `cookies.txt`；之后 Downtify 会自动保持该会话的登录状态。如果 YouTube 仍然限制你，请增大 _下载间隔_，减少 _并行下载数_，然后尝试 `DOWNTIFY_FORCE_IPV4=1`。参见[故障排查](troubleshooting.md)和 [YouTube Cookie](features/youtube-cookies.md)。
:::

## 随身携带

<HomeHighlights :items="$frontmatter.apps" />

其他任何客户端都可以使用同一套 API：参见[移动客户端协议](mobile-client-contract.md)。

<div class="home-cta">

## 公开构建

Downtify 是自由开源软件。超过 35 人贡献过代码，社区译者把它带到了 12 种语言，许多功能都始于某人在 issue 中提出的想法。如果它在你的服务器上赢得了一席之地，欢迎在 GitHub 上加星、推荐给同样自托管服务的朋友，或赞助它的开发：这有助于支付每个版本所投入的时间。

<HomeActions :actions="$frontmatter.community" />

</div>
