---
icon: lucide/play
---

# 快速入门

Downtify 是一款自托管 Web 应用，可从 Spotify 下载音乐，无需 API 密钥、账号或 Premium 订阅。所有服务都运行在一个 Docker 容器中。

## 你需要准备

- **Docker**（或 Docker Compose）：主机上唯一需要的软件
- 可访问互联网的设备
- 用于保存音乐的卷或目录

## 选择部署方式

<div class="doc-cards">

- <DocIcon name="docker" /> **Docker run**

  最快的启动方式。一条命令，不到一分钟即可运行。

  [安装指南 →](installation.md)

- <DocIcon name="file-code" /> **Docker Compose**

  推荐用于长期运行的部署，更新和管理更方便。

  [Docker Compose →](docker-compose.md)

- <DocIcon name="house" /> **One-click install**

  使用 Umbrel、CasaOS 或 HomeDock OS？可以直接从其应用商店安装。

  [一键安装 →](one-click.md)

</div>

## 后续步骤

Downtify 启动后，在浏览器中打开 [http://localhost:8000](http://localhost:8000)。将 Spotify 歌曲、专辑或播放列表链接粘贴到搜索栏，然后点击 **Download**。

继续阅读文档，了解[下载设置](../features/download-settings.md)、[播放列表监控](../features/playlist-monitor.md)、[内置播放器](../features/player.md)等功能。
