---
icon: lucide/trending-up
---

# 排行榜

**Charts** 展示 Deezer 的全球榜单，反映当前全球热门内容，不按流派筛选，也无需 Deezer 账号或 API 密钥。

## 使用方法

从侧边栏（手机上从 **More** 菜单）打开 **Charts**。四个标签页展示同一榜单中的不同类型：**Tracks**、**Albums**、**Artists** 和 **Playlists**。

- **Tracks**：按排名排列的曲目列表。点击歌曲或其所在行，可在下载前通过内置播放器从 YouTube 完整试听。点击下载时，Downtify 会像处理搜索结果一样，在 YouTube Music（必要时回退到普通 YouTube）上按标题、艺人和时长查找最匹配的音频，使用与其他下载相同的[匹配流程](../how-it-works.md)。歌曲下载后，该行会改为播放媒体库中的本地文件。
- **Albums**、**Artists** 和 **Playlists**：封面网格。点击项目后会解析链接（[`GET /api/url/resolve`](../api-reference.md#get-apiurlresolve)），与将 Deezer 链接粘贴到搜索框的处理方式相同；加载曲目列表后即可选择并下载。

## 为什么歌曲能直接从排行榜下载和完整播放，而专辑、艺人和播放列表要先打开页面

排行榜歌曲无需额外解析：Deezer 已提供标题、艺人和专辑名称，足以像自由文本搜索结果一样在 YouTube 上搜索并匹配。专辑、艺人或播放列表则需要先将链接解析为曲目列表，因此点击卡片会打开解析后的页面，而不是直接从网格下载。歌曲行会从 YouTube 完整串流播放（专辑、艺人和播放列表不会这样播放）；其他页面的歌曲行也采用相同的串流方式，只是这里使用榜单提供的标题和艺人信息。

## 监控或保存排行榜播放列表

每张播放列表封面上都有 **⋯** 菜单，提供下载以外的两项操作：

- **Watch for new tracks**：添加一个[播放列表监控](playlist-monitor.md#deezer-playlists)，每 6 小时检查一次。首次检查会下载播放列表中的现有歌曲，之后的检查会下载新添加的歌曲。可在 **Monitor** 页面修改间隔、暂停或停止监控。
- **Add to my playlists**：打开播放列表选择器，其中列出**已在媒体库中**的歌曲，可将它们添加到现有播放列表，或新建一个以该榜单播放列表命名的播放列表。此操作不会下载歌曲，也不会在之后跟随榜单播放列表更新；如需这些行为，请使用下载按钮或 **Watch for new tracks**。如果媒体库中还没有其中任何歌曲，界面会相应提示。

## API

API 说明请参阅 API 参考中的 [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart)。
