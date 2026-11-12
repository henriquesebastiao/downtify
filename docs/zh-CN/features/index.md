---
icon: lucide/sparkles
---

# 功能

Downtify 提供构建和维护本地音乐库所需的各种功能。

## 功能概览

| 功能 | 说明 |
|---------|-------------|
| [排行榜](charts.md) | 浏览 Deezer 全球排行榜，下载当前热门内容 |
| [相似歌曲](similar.md) | 输入艺人或歌曲名称，通过 YouTube Music 查找可完整播放和下载的相似歌曲，无需密钥 |
| [查找](finder.md) | 搜索 Deezer，并按艺人、专辑和曲目分栏浏览 |
| [下载设置](download-settings.md) | 选择格式（MP3/FLAC/M4A/OGG/OPUS）、比特率、并行下载数和下载间隔 |
| [下载队列](download-queue.md) | 更改设置或更新前暂停下载；正在运行的任务会完成，等待中的歌曲会保留，重启后可继续 |
| [播放列表监控](playlist-monitor.md) | 监控 Spotify 或 YouTube Music 播放列表和艺人，自动下载新曲目和新发行内容 |
| [隐藏的播放列表歌曲](hidden-playlist-songs.md) | 从已下载或正在监控的播放列表中排除不需要的歌曲，文件仍保留在媒体库 |
| [协作播放列表](collaborative-playlists.md) | 允许指定共享媒体库播放列表的用户添加或移除歌曲；重命名、分享和删除仍由你管理 |
| [播放列表顺序与重复歌曲](playlist-order.md) | 按任意顺序排列媒体库播放列表中的歌曲，并可在其中多次播放同一首歌曲 |
| [热门歌曲](top-songs.md) | 粘贴艺人链接，下载其热门歌曲，也可将歌曲加入播放列表 |
| [导入媒体库（CSV）](library-import.md) | 导入 Soundiiz、TuneMyMusic 或 Exportify 导出的媒体库，并将曲目加入队列 |
| [内置播放器](player.md) | 在浏览器中播放媒体库，支持队列管理、同步歌词、睡眠定时器、键盘和媒体按键 |
| [音量标准化](playback-normalization.md) | 根据管理员发起的响度测量，让歌曲播放音量更接近；不会修改音频文件 |
| [已点赞歌曲](liked-songs.md) | 点赞歌曲后，Downtify 会自动生成包含所有已点赞歌曲的播放列表 |
| [播客](podcasts.md) | 通过 RSS feed、Spotify 链接或名称订阅节目；新剧集会自动下载并写入标签 |
| [用户与登录](users.md) | 用户名密码登录（新服务器默认 `admin` / `downtify`）、管理员和普通用户账号、个人偏好设置，以及登录和播放活动日志 |
| [显式内容标记](explicit-marker.md) | 在搜索、媒体库和播放器中显示带显式歌词歌曲的“E”标记，并写入文件标签 |
| [替换音频](replace-audio.md) | 歌曲或版本不正确时，在 YouTube Music 或 YouTube 上选择正确音频；文件名、标签和播放列表保持不变 |
| [服务器设置](server.md) | 由管理员在设置中更改 Downtify 监听端口，并可选择立即重启 |
| [移动应用](mobile-apps.md) | 通过二维码配对手机应用，并向其传输原始或转码后的媒体库音频 |
| [发现](discover.md) | 根据媒体库、点赞和收听记录推荐尚未收藏的艺人、专辑和播放列表；可隐藏不感兴趣的内容 |
| [slskd 与 Navidrome](slskd-navidrome.md) | 通过 slskd 从 Soulseek 下载、将播放列表同步到 Navidrome，并跟踪播放列表下载 |
| [媒体库目录与路径同步](library-catalog.md) | 了解 Downtify 如何跟踪媒体库文件和播放列表，以及如何创建媒体库播放列表、移动文件后修复路径 |
| [现有音乐文件夹](external-library.md) | 指定已有音频文件夹；同步时读取标签、匹配艺人并跳过媒体库中已有的歌曲 |
| [升级媒体库](library-upgrade.md) | 扫描已下载的音乐，修复低分辨率封面、缺失歌词和不完整标签 |
| [存储空间与用量](storage-usage.md) | 查看媒体库大小和增长速度、各部分来源、下载结果，以及重复文件、slskd 副本和残留文件的占用 |
| [导出 M3U](m3u-export.md) | 自动生成播放列表文件，供 Jellyfin、Navidrome、Plex 和其他媒体应用读取 |
| [播放列表封面](playlist-cover-art.md) | 将播放列表专属封面与其 M3U 文件一起保存 |
| [艺人照片、横幅与简介](artist-images.md) | 从 YouTube Music、Deezer、Spotify 或自定义上传中选择艺人照片和横幅，并按需或自动从 Apple Music 和 Deezer 获取简介、来源地和链接 |
| [支持艺人](support-artists.md) | 查找歌曲、专辑或艺人的购买渠道，包括带价格的 iTunes Store 商品、Bandcamp、Qobuz 和艺人网站 |
| [文件整理](file-organization.md) | 选择平铺目录或按艺人分类的子目录 |
| [歌词](lyrics.md) | 自动下载并嵌入普通歌词和逐字同步歌词；可将 `.lrc` 文件放在音频旁边或指定目录 |
| [YouTube Cookie](youtube-cookies.md) | 在 Web 界面上传 `cookies.txt`，以下载显式内容或年龄限制歌曲 |
| [国际化](internationalization.md) | 开箱即用提供英语及其他语言的应用和文档翻译 |
| [更新通知](updates.md) | 每小时检查 GitHub Releases；有新版本时在侧边栏显示通知 |

## 支持的输入类型

Downtify 的搜索栏支持以下输入：

| 输入 | 示例 |
|-------|---------|
| Spotify 歌曲、专辑、播放列表或艺人链接 | `https://open.spotify.com/track/…` |
| YouTube / YouTube Music 链接 | `https://www.youtube.com/watch?v=…` |
| YouTube Music 播放列表或艺人链接 | `https://music.youtube.com/playlist?list=…` |
| Deezer 歌曲、专辑、播放列表或艺人链接 | `https://www.deezer.com/track/…` |
| SoundCloud 歌曲链接（[详情](soundcloud.md)） | `https://soundcloud.com/artist/track` |
| 自由文本搜索 | `The Night Owls Do I Still Recall` |

自由文本搜索会直接发送到 YouTube Music，无需 Spotify 链接。
