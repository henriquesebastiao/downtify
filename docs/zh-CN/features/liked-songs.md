---
icon: lucide/heart
---

# 喜欢的歌曲

点击歌曲旁的心形图标即可表示喜欢。喜欢第一首歌曲后，Downtify 会自动创建一个包含所有已喜欢歌曲的 **Liked songs** 播放列表，让你在 Downtify 和任何连接到媒体库的媒体服务器中都能快速找到收藏。

无需启用任何设置。

每位用户的心形标记互相独立：在包含多个账户的服务器上，每个人都有自己的喜欢列表（参见[用户与登录](users.md#your-library)）。磁盘上的播放列表文件保存管理员的喜欢记录；其他用户的喜欢记录存储在媒体库数据库中，在应用中的表现相同。

## 喜欢歌曲

Library 中每首歌曲旁边都有心形图标，包括已下载歌曲和来自[现有音乐文件夹](external-library.md)的曲目：

- 曲目列表中，包括 Library、专辑、艺人和播放列表页面；
- [播放器栏](player.md#player-bar)中（屏幕宽度不小于 640px 时）；
- [Now playing](player.md#now-playing) 页面中，位于歌曲标题旁。

点击图标即可喜欢，再次点击可取消喜欢。图标会变为绿色，修改会立即同步到服务器，因此在手机上点击后，桌面端也会同步更新；已打开的标签页和设备会自动跟进。

只有媒体库中的歌曲可以被喜欢。尚未下载的搜索结果没有心形图标，请先下载歌曲。

## 播放列表

第一次喜欢歌曲时会创建播放列表，并显示一条可打开该列表的提示。它与其他播放列表一样会显示在侧边栏、Home 页面以及 **Library → Playlists** 中，但始终排在**第一位**，并以心形图标代替封面。歌曲按最近喜欢的时间倒序排列。

取消最后一首歌曲的喜欢后，播放列表也会随之删除，不会留下空的 **Liked songs** 列表。

列表标题会根据你的[语言](internationalization.md)显示。在磁盘上，它是一个名称固定的普通 [M3U 文件](m3u-export.md)：

```
<downloads>/Playlists/Downtify Liked Songs.m3u
```

因此 Jellyfin、Navidrome、Plex 等媒体服务器也能显示此列表：它们读取的是同一个文件。该名称有意保留，因为 Spotify 上常见名为 *Liked Songs* 的播放列表；若下载的同名列表使用相同文件名，就会发生冲突。

## 清除所有喜欢记录

打开播放列表，选择 **⋯ → Remove all likes** 并确认。所有心形标记都会清除，播放列表也会删除。

::: info 歌曲文件会保留
清除喜欢记录不会删除音频文件，只会移除心形标记和播放列表。删除已下载的普通播放列表则可能删除其中的歌曲；**Liked songs** 不会按这种方式处理。在应用中或通过 [API](../api-reference.md#delete-apilibraryplaylist) 请求删除该列表，只会清除喜欢记录。
:::

## 文件与喜欢记录保持同步

喜欢记录会跟随它所关联的文件：

| 文件发生的情况 | 喜欢记录的处理方式 |
|--------------------------|--------------------------|
| 在 Downtify 中删除歌曲 | 对应喜欢记录一并删除，并重写播放列表 |
| 移动文件并运行[修复媒体库路径](library-catalog.md#fix-library-paths) | 喜欢记录会随文件迁移到新位置 |
| 文件在 Downtify 之外消失（例如驱动器未挂载或手动删除） | 保留喜欢记录，但歌曲会暂时从播放列表中排除，直到文件重新出现 |

保留丢失文件对应的喜欢记录，可以避免拔掉驱动器就丢失收藏。如果你在 Downtify 之外手动删除了文件，并希望同时清除喜欢记录，请使用 **Remove all likes**，或在删除文件前取消喜欢。

## 注意事项

- 喜欢记录存储在媒体库数据库（`/data` 卷中的 `downtify_library.db`）内，不会写入音频文件标签。
- Downtify 不会在 [Navidrome](slskd-navidrome.md) 中创建播放列表。这是一个普通 M3U 文件，因此媒体服务器如何处理它取决于该服务器对 M3U 文件的读取方式。
- 即使下载设置中的 *Write M3U playlists* 已关闭，[播放列表文件](m3u-export.md)仍会写入，因为该文件正是此功能的一部分。

## API

`GET /api/likes`、`PUT /api/likes` 和 `POST /api/likes/clear`，以及 [`GET /playlists`](../api-reference.md#get-playlists) 中的 `liked` 标记。详见 [API 参考](../api-reference.md#likes)。
