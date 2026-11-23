---
icon: lucide/sparkles
---

# 功能

Downtify 的全部功能，按侧边栏中的领域分组。每个功能都有自己的页面，详细说明每个选项。

## 发现音乐

| 功能 | 说明 |
|---------|-------------|
| [发现](discover.md) | 根据媒体库、点赞和收听记录推荐尚未收藏的艺人、专辑和播放列表；可隐藏不感兴趣的内容 |
| [排行榜](charts.md) | 浏览 Deezer 全球排行榜，下载当前热门内容 |
| [查找](finder.md) | 搜索 Deezer，并按艺人、专辑和曲目分栏浏览 |
| [相似歌曲](similar.md) | 输入艺人或歌曲名称，通过 YouTube Music 查找可完整播放和下载的相似歌曲，无需密钥 |
| [热门歌曲](top-songs.md) | 粘贴艺人链接，下载其热门歌曲，也可将歌曲加入播放列表 |
| [支持艺人](support-artists.md) | 查找歌曲、专辑或艺人的购买渠道，包括带价格的 iTunes Store 商品、Bandcamp、Qobuz 和艺人网站 |

## 下载

| 功能 | 说明 |
|---------|-------------|
| [下载设置](download-settings.md) | 选择格式（MP3/FLAC/M4A/OGG/OPUS）、比特率、并行下载数和下载间隔 |
| [下载队列](download-queue.md) | 更改设置或更新前暂停下载；正在运行的任务会完成，等待中的歌曲会保留，重启后可继续 |
| [下载排除](download-exclusions.md) | 停止重试反复失败的歌曲，并限制一次下载最多可以尝试多长时间 |
| [导入媒体库（CSV）](library-import.md) | 导入 Soundiiz、TuneMyMusic 或 Exportify 导出的媒体库，并将曲目加入队列 |
| [YouTube Cookie](youtube-cookies.md) | 在 Web 应用中上传 `cookies.txt`，以通过 YouTube 的机器人验证并下载有年龄限制的歌曲 |

## 媒体库

| 功能 | 说明 |
|---------|-------------|
| [媒体库目录与路径同步](library-catalog.md) | 了解 Downtify 如何跟踪媒体库文件和播放列表，以及如何创建媒体库播放列表、移动文件后修复路径 |
| [现有音乐文件夹](external-library.md) | 指定已有音频文件夹；同步时读取标签、匹配艺人并跳过媒体库中已有的歌曲 |
| [升级媒体库](library-upgrade.md) | 扫描已下载的音乐，修复低分辨率封面、缺失歌词和不完整标签 |
| [按声音识别歌曲](acoustid.md) | 用 AcoustID 按声音识别旧文件（可选），匹配确定时添加 ISRC |
| [替换音频](replace-audio.md) | 歌曲或版本不正确时，在 YouTube Music 或 YouTube 上选择正确音频；文件名、标签和播放列表保持不变 |
| [艺人照片、横幅与简介](artist-images.md) | 从 YouTube Music、Deezer、Spotify 或自定义上传中选择艺人照片和横幅，并按需或自动从 Apple Music 和 Deezer 获取简介、来源地和链接 |
| [存储空间与用量](storage-usage.md) | 查看媒体库大小和增长速度、各部分来源、下载结果，以及重复文件、slskd 副本和残留文件的占用 |
| [音乐回收站](music-trash.md) | 可选：删除的歌曲会在回收站中保留 30 天，可连同点赞和播放列表一起恢复 |
| [医生](doctor.md) | 找出旧版本留下的内容，例如 Soulseek 下载的第二份副本或 Navidrome 中重复的播放列表，并修复确认安全的部分 |

## 标签与文件

| 功能 | 说明 |
|---------|-------------|
| [文件整理](file-organization.md) | 按 `艺人/专辑` 分目录或平铺目录，以及多位艺人的歌曲和合辑存放位置 |
| [歌词](lyrics.md) | 自动下载并嵌入普通歌词和逐字同步歌词；可将 `.lrc` 文件放在音频旁边或指定目录 |
| [显式内容标记](explicit-marker.md) | 在搜索、媒体库和播放器中显示带显式歌词歌曲的“E”标记，并写入文件标签 |

## 播放列表

| 功能 | 说明 |
|---------|-------------|
| [播放列表监控](playlist-monitor.md) | 监控 Spotify、Deezer 和 YouTube Music 的播放列表和艺人，按你设定的频率下载新曲目和新发行内容 |
| [播放列表显示名称](playlist-names.md) | 更改导入或同步的播放列表的显示名称，不影响其来源和同步 |
| [收藏的播放列表](playlist-favorites.md) | 将播放列表固定在列表和首页顶部，网页和应用中都生效 |
| [隐藏的播放列表歌曲](hidden-playlist-songs.md) | 从已下载或正在监控的播放列表中排除不需要的歌曲，文件仍保留在媒体库 |
| [协作播放列表](collaborative-playlists.md) | 允许指定共享媒体库播放列表的用户添加或移除歌曲；重命名、分享和删除仍由你管理 |
| [播放列表顺序与重复歌曲](playlist-order.md) | 按任意顺序排列媒体库播放列表中的歌曲，并可在其中多次播放同一首歌曲 |
| [播放列表封面](playlist-cover-art.md) | 将播放列表封面与其 M3U 文件一起保存，或为自己创建的播放列表上传封面 |
| [导出 M3U](m3u-export.md) | 自动生成播放列表文件，供 Jellyfin、Navidrome、Plex 和其他媒体应用读取 |
| [导入现有播放列表](external-playlists.md) | 将音乐文件夹中的 M3U 和 M3U8 播放列表导入媒体库，直接指向已有的文件 |

## 收听

| 功能 | 说明 |
|---------|-------------|
| [内置播放器](player.md) | 在浏览器中播放媒体库，支持同步歌词、卡拉OK、可编辑队列、睡眠定时器、键盘快捷键和媒体按键 |
| [音量标准化](playback-normalization.md) | 根据管理员发起的响度测量，让歌曲播放音量更接近；不会修改音频文件 |
| [已点赞歌曲](liked-songs.md) | 点赞歌曲后，Downtify 会自动生成包含所有已点赞歌曲的播放列表 |
| [播客](podcasts.md) | 通过 RSS feed、Spotify 链接或名称订阅节目；新剧集会自动下载并写入标签 |
| [移动应用](mobile-apps.md) | 在 Android 和 iOS 应用中登录，或通过二维码配对，并向其传输原始或转码后的媒体库音频 |
| [安装为应用](pwa.md) | 将 Downtify 添加到手机主屏幕，像原生应用一样全屏打开 |

## 音源与集成

| 功能 | 说明 |
|---------|-------------|
| [SoundCloud](soundcloud.md) | 粘贴 SoundCloud 歌曲链接，并将 SoundCloud 作为其他来源缺失歌曲的音源 |
| [Deemix](deemix.md) | 使用你自己的 Deemix 服务器和 Deezer 账号作为音源 |
| [slskd 与 Navidrome](slskd-navidrome.md) | 通过 slskd 从 Soulseek 下载、将播放列表同步到 Navidrome，并跟踪播放列表下载 |
| [来自 Deezer 的评分](navidrome-ratings.md) | 根据歌曲在 Deezer 上的热度，为 Navidrome 中的歌曲打 0–5 星 |
| [Aurral](aurral.md) | 让 Aurral 把 Downtify 当作下载来源：Aurral 发出请求，Downtify 下载，Aurral 把结果放进自己的音乐库 |

## 服务器与账户

| 功能 | 说明 |
|---------|-------------|
| [用户与登录](users.md) | 用户名密码登录（新服务器默认 `admin` / `downtify`）、管理员和普通用户账号、个人偏好设置，以及登录和播放活动日志 |
| [服务器设置](server.md) | 由管理员在设置中更改 Downtify 监听端口，并可选择立即重启 |
| [备份](backups.md) | 按计划或随时备份设置、监控项和歌曲列表，在磁盘丢失后或在新服务器上恢复 |
| [通知](notifications.md) | 把长任务（医生、媒体库升级、评分、备份）和下载的消息发到 Discord、ntfy、Gotify 或 webhook，并支持 `/status` 等 Discord 命令 |
| [仅媒体库模式](library-only.md) | 将所有账号和应用限制在媒体库中已有的音乐：不进行外部搜索、流式播放或下载 |
| [出站代理](outbound-proxy.md) | 通过 HTTP、HTTPS 或 SOCKS5 代理发送 Downtify 的出站流量 |
| [更新通知](updates.md) | 每小时检查 GitHub Releases；有新版本时在侧边栏显示通知，更新后显示新功能摘要 |
| [国际化](internationalization.md) | 应用支持 12 种语言，文档覆盖其中几乎所有语言，并说明如何添加你的语言 |

## 支持的输入类型

Downtify 的搜索栏支持多种输入类型：

| 输入 | 示例 |
|-------|---------|
| Spotify 歌曲、专辑、播放列表或艺人链接 | `https://open.spotify.com/track/…` |
| YouTube / YouTube Music 链接 | `https://www.youtube.com/watch?v=…` |
| YouTube Music 播放列表或艺人链接 | `https://music.youtube.com/playlist?list=…` |
| Deezer 歌曲、专辑、播放列表或艺人链接 | `https://www.deezer.com/track/…` |
| SoundCloud 歌曲链接（[详情](soundcloud.md)） | `https://soundcloud.com/artist/track` |
| 自由文本搜索 | `The Night Owls Do I Still Recall` |

自由文本搜索会直接发送到 YouTube Music，无需 Spotify 链接。
