---
icon: lucide/shield-alert
---

# 显式内容标记

含有露骨歌词（不适合儿童的语言）的歌曲会像 Spotify 一样在标题旁显示小小的 **E**。无论下载前后，只要遇到这首歌都会显示该标记，并且标记也会写入文件。

## 显示位置

- **搜索结果、粘贴的链接、排行榜和 Finder**：服务标记为显式内容的歌曲会显示标记，下载前即可识别。
- **Library**：Tracks 标签页、专辑/艺人/播放列表页面，以及“添加歌曲”选择器中。
- **播放器**：播放器栏、**Now playing** 和 **Up next** 中的歌曲标题旁。

将鼠标悬停在 **E** 上（或使用屏幕阅读器读取）即可看到“Explicit”。

## 标记来源

标记由下载来源决定：Spotify、YouTube Music 和 Deezer 都会标记显式内容，Downtify 使用你所选来源提供的信息。Downtify 从 YouTube Music 下载歌曲时，标记反映的是**实际下载的视频**：如果 Spotify 上的歌曲属于显式内容，但 Downtify 匹配到的是洁净版，则文件不会标记；反之，如果 Spotify 将歌曲标为洁净版，但匹配结果属于显式内容，则文件会标记。

服务没有标记的歌曲不会显示任何标记。这不代表歌曲已获认证为洁净版，Downtify 也不会写入“洁净”标记。

## 写入文件

此标记会以与 iTunes 相同的方式写入文件标签，因此支持该标签的媒体服务器和播放器也可以使用它。Navidrome 会读取这些标签来确定曲目的显式内容状态。

| 格式 | 标签 |
|--------|-----|
| MP3 | `ITUNESADVISORY` 文本帧（`TXXX`），值为 `1` |
| FLAC、OGG、OPUS | `ITUNESADVISORY` 注释，值为 `1` |
| M4A | `rtng` atom，值为 `1` |

Downtify 也会用相同方式读取已有文件：由 iTunes、MusicBrainz Picard 或其他标签编辑器标记为 `1`（或旧值 `4`）的文件也会显示 **E**，包括来自[额外文件夹](external-library.md)的歌曲。

::: info 更新前下载的歌曲
在该标记功能加入前由 Downtify 写入的文件没有相应标签，因此不会显示 **E**，即使歌曲实际属于显式内容。可以使用 [Replace audio](replace-audio.md) 或重新下载歌曲来写入标记。通过 [Upgrade library](library-upgrade.md) 或 Replace audio 重写文件时会保留标记：Downtify 只会添加标记，不会清除标记。
:::

更新后首次加载 Library 时，Downtify 会重新读取所有文件标签来查找该标记，与新增编解码器和流派信息时的处理方式相同。对于磁盘较慢的大型媒体库，此过程可能会短暂耗时，但只会执行一次。

## 面向应用开发者

[移动客户端协议](../mobile-client-contract.md)和 [API 参考](../api-reference.md#get-tracks)说明了 `explicit` 字段：显式曲目为 `true`，其他曲目不包含此字段。
