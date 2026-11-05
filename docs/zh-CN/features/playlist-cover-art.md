---
icon: lucide/image
---

# 播放列表封面

Downtify 可以将播放列表自己的封面保存在其 [M3U 文件](m3u-export.md)旁边，让媒体服务器和文件浏览器显示真实封面，而非通用图标。

此功能默认启用。可在 **Settings → Downloads & files → Save playlist cover art** 中关闭。

## 封面文件位置

封面使用与播放列表 M3U **相同的文件名和文件夹**，扩展名改为 `.jpg`：

```
<downloads>/<playlist-name>/<playlist-name>.m3u
<downloads>/<playlist-name>/<playlist-name>.jpg
```

启用 *Organize by artist* 或 *Organize by album* 后，曲目会分散到各艺人文件夹，而 M3U 会移到中央 `Playlists/` 目录（参见[文件整理](file-organization.md)），封面也会与它放在一起：

```
<downloads>/Playlists/<playlist-name>.m3u
<downloads>/Playlists/<playlist-name>.jpg
```

::: info 需要 M3U 文件
如果关闭 **Write M3U playlists**，也不会保存封面：Downtify 会按 M3U 的路径放置图片，没有 M3U 就没有目标位置。当关闭 M3U 写入时，此设置也会隐藏。
:::

## 来源和分辨率

| 来源 | 分辨率 |
|--------|-----------|
| **Spotify** | Spotify 公共 embed 页面为播放列表提供的最大图片，也就是已用于曲目封面的图片 |
| **YouTube Music** | 始终请求 1200×1200，不受[封面分辨率](download-settings.md#cover-art-resolution)设置影响；该设置只控制单曲封面 |

这两个来源的 URL 均返回 JPEG，即使原始封面是 PNG，因此文件始终保存为 `.jpg`。

## 下载时机

两种情况下都会在**曲目下载前**获取封面，使文件夹从一开始就呈现播放列表封面；即使媒体服务器在下载过程中扫描，也能看到封面而非空白文件夹：

- **手动下载播放列表**：解析出播放列表名称后立即下载一次，再开始第一首曲目。
- **[播放列表监控](playlist-monitor.md)**：每次确实有新曲目需要下载的扫描任务开始前获取一次。没有新曲目的扫描不会重新获取封面。

封面无法解析或下载（例如网络错误或播放列表没有封面）时会记录日志并跳过，不会阻塞或导致下载失败。

## Downtify 界面中的显示

通过 Spotify 或 YouTube 播放列表下载且拥有专属封面的播放列表，会在媒体库的网格、播放列表页面、侧边栏和播放器中显示该封面。没有专属封面的播放列表以及在 Library 中创建的播放列表，会使用最多四张不同曲目封面拼成网格：两张时左右排列，三张时左侧为大图、右侧上下排列两张，四张时按 2×2 排列。相同拼图也会保存为手动创建播放列表的 `<playlist-name>.jpg`，与其 M3U 文件放在一起供 Navidrome 使用；添加或移除歌曲时会重新生成封面。

在自建播放列表中选择 **Upload cover**，可使用自定义 JPEG、PNG 或 WebP 图片（最大 10 MiB）。Downtify 会将其转换为 M3U 文件旁的 `.jpg`，并显示在媒体库、播放列表页面和播放器的播放列表上下文中。只有播放列表所有者和管理员可以上传或删除封面。点击 **Remove cover** 会恢复自动生成的曲目封面拼图。

## Navidrome

无需额外配置：Navidrome 会从**旁置图片**解析播放列表封面，也就是与播放列表同目录且文件名一致的图片，正是 Downtify 生成的格式。只要 Navidrome 的音乐目录包含下载目录，下一次扫描就会显示封面。Downtify 不会调用 Navidrome API。参见 [slskd 与 Navidrome](slskd-navidrome.md#navidrome)。

## 清理

在 Library 页面删除播放列表时，其封面会与 M3U 和曲目一并删除。参见[删除播放列表](slskd-navidrome.md#deleting-a-playlist)。
