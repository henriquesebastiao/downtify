---
layout: home
title: Downtify
titleTemplate: 自托管音乐下载器
description: 自托管音乐下载器。粘贴 Spotify 链接，即可获取标签完整的音频文件，无需 API 密钥、账号或 Premium 订阅。
icon: lucide/house
hero:
  eyebrow: 自托管音乐下载器
  lead:
    - 可部署在自己设备上的音乐下载器。
    - 粘贴 Spotify 链接，即可获取带完整标签的音频文件。无需账号、API 密钥或 Premium。
  actions:
    - text: 快速入门
      link: /getting-started/installation/
      primary: true
    - text: 在 GitHub 上查看源码
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: 发行版本
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker 拉取量
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: 许可证
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: 元数据
  - title: YouTube Music
    text: 音频匹配
  - title: yt-dlp · ffmpeg · mutagen
    text: 下载并写入标签
highlights:
  - icon: eye
    title: 播放列表监控
    text: 持续监控播放列表，并在添加新曲目时自动下载。
    link: /zh-CN/features/playlist-monitor/
  - icon: sliders-horizontal
    title: 五种音频格式
    text: 支持 MP3、FLAC、M4A、OGG 和 OPUS，并可自行选择比特率。
    link: /zh-CN/features/download-settings/
  - icon: mic-vocal
    title: 内嵌歌词
    text: 从 lrclib 获取普通歌词和逐字同步歌词，并嵌入音频文件。
    link: /zh-CN/features/lyrics/
  - icon: headphones
    title: Web 播放器
    text: 直接在浏览器中播放，支持随机播放、循环、音量控制和专辑封面。
    link: /zh-CN/features/player/
  - icon: list-music
    title: 导出 M3U
    text: 生成标准 EXTM3U 文件，供 Jellyfin、Navidrome 和 Plex 自动读取。
    link: /zh-CN/features/m3u-export/
  - icon: folder
    title: 媒体库布局
    text: 可选择平铺目录或按艺人分类，满足媒体服务器的整理偏好。
    link: /zh-CN/features/file-organization/
  - icon: import
    title: 导入 CSV 媒体库
    text: 导入 Soundiiz、TuneMyMusic 或 Exportify 导出的文件，一次性将曲目加入队列。
    link: /zh-CN/features/library-import/
quickStart:
  - text: 安装指南
    link: /zh-CN/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /zh-CN/getting-started/docker-compose/
---

## 工作原理

Spotify 官方 API 要求用户订阅 Premium 才能下载。Downtify 使用另一种方式：读取 Spotify 公开 embed 页面提供的元数据，在 YouTube Music 上查找最匹配的音频，再交由 `yt-dlp` 和 `ffmpeg` 处理，并使用 `mutagen` 写入规范标签。整个流程都运行在一个 Docker 容器中。

<HomePipeline :steps="$frontmatter.pipeline" />

## 支持粘贴的内容

|                    |                                    |
| ------------------ | ---------------------------------- |
| Spotify 歌曲 | `open.spotify.com/track/…` |
| Spotify 专辑 | `open.spotify.com/album/…` |
| Spotify 播放列表 | `open.spotify.com/playlist/…` |
| YouTube / YouTube Music | `youtube.com/watch?v=…` |
| 自由文本搜索 | `The Night Owls Do I Still Recall` |

## 主要功能

<HomeHighlights :items="$frontmatter.highlights" />

## 一条命令即可启动

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

打开 [`localhost:8000`](http://localhost:8000)，粘贴链接并点击下载。文件会保存到 `/path/to/music`，并自动写入标签。

<HomeActions :actions="$frontmatter.quickStart" />
