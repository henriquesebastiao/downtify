---
icon: lucide/eye-off
---

# 隐藏的播放列表歌曲

从 Spotify、YouTube Music 或 Deezer 链接下载的播放列表会跟随来源变化；[播放列表监控](playlist-monitor.md)也会在每次扫描时同步更新。自动生成的播放列表和电台可能包含你不想要的歌曲；如果手动从 M3U 中删除，下一次扫描又会将其写回。使用 **Hide from playlist** 可将歌曲从列表移除并持续隐藏。

## 隐藏歌曲

在播放列表页面打开歌曲的 **⋯** 菜单，然后选择 **Hide from playlist**。确认提示中提供 **Undo** 操作。

隐藏后：

- **歌曲会立即从播放列表中移除**：它会从播放列表的 [M3U 文件](m3u-export.md)中删除，因此读取该文件的媒体服务器也会移除该曲目；启用了 [Navidrome 同步](slskd-navidrome.md)时，Navidrome 播放列表也会同步更新。
- **文件仍保留在媒体库**，可以从其专辑、艺人和其他播放列表中搜索并播放。如需同时删除文件，请在 Library 中对歌曲使用 **Delete**。
- **监控扫描会继续排除该歌曲**：不会重新加入 M3U，也不会再次下载，即使你删除了音频文件也一样。
- **该歌曲不再视为缺失**：**Download missing** 会跳过它，播放列表可以在不包含此歌曲的情况下视为完整。
- **再次从链接下载播放列表**时，隐藏的歌曲仍不会加入播放列表。

Spotify 或 YouTube Music 上的原始播放列表不会改变：Downtify 无需账号即可读取来源，因此无法编辑来源列表。

只有播放列表所有者（或管理员）可以隐藏歌曲。被[共享播放列表](users.md#sharing-playlists)的用户会看到所有者维护的列表。播放列表至少要保留一首歌曲；如需清空，请删除整个播放列表。

::: info 在 Library 中创建的播放列表
Library 播放列表没有外部来源会重新添加歌曲，因此可以直接使用 **Remove from playlist** 编辑。对导入播放列表使用 **Detach from source** 时会像取消隐藏一样处理歌曲：歌曲不再位于播放列表中，但之后仍可像其他歌曲一样重新添加。
:::

## 恢复显示歌曲

隐藏了歌曲的播放列表会在曲目列表下方显示 **N hidden songs**。点击 **Show tracks** 可查看隐藏列表，再点击 **Show again** 即可将歌曲放回播放列表原来的位置。

如果歌曲文件已经删除，会显示 **No longer in your library**。恢复显示只会取消隐藏；下一次监控扫描或点击 **Download missing** 时，Downtify 会像处理其他缺失歌曲一样重新下载它。

## 应用中的行为

应用也按曲目 ID 使用相同规则隐藏歌曲，并可通过相同方式查看和恢复。参见 [`POST /api/v1/playlists/hidden`](../api-reference.md#post-apiv1playlistshidden) 和[移动客户端协议](../mobile-client-contract.md)。
