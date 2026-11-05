---
title: SoundCloud
icon: lucide/cloud
---

# SoundCloud

Downtify 支持两种 SoundCloud 用法：粘贴 **SoundCloud 曲目链接**下载指定曲目；也可以将 **SoundCloud** 添加为音频来源，在 Spotify、YouTube Music 或 Deezer 链接对应的歌曲无法从其他来源找到时，继续到 SoundCloud 搜索。两种方式都使用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 的 SoundCloud 支持，无需 SoundCloud 账号。

## 启用 SoundCloud

SoundCloud 默认关闭。在 **Settings → Audio sources** 中点击 **SoundCloud** 将其加入来源顺序，然后使用箭头调整位置。每首歌曲会按顺序尝试已启用的来源，并在第一个找到歌曲的来源处停止。来源顺序详见 [slskd 与 Navidrome](slskd-navidrome.md#audio-sources-and-fallback-order)。

大多数情况下建议将它放在最后：SoundCloud 适合寻找混音、DJ 编辑版以及未收录于大型曲库的上传内容；其他曲目通常在 YouTube Music 上能找到音质更好的版本。

## SoundCloud 链接

将曲目链接粘贴到搜索栏，然后点击 **Get it**：

| 链接 | 示例 |
|------|---------|
| 曲目 | `soundcloud.com/artist/track-name` |
| 私密曲目（通过秘密链接分享） | `soundcloud.com/artist/track-name/s-AbC123` |

包含 `www.` 和 `m.` 的链接也可使用，分享按钮添加的 `?si=…` 参数会被移除。不支持 Sets（专辑和播放列表）、用户主页以及简短的 `on.soundcloud.com` 链接。请先在浏览器中打开短链接，再粘贴它跳转到的完整链接。

曲目信息来自 SoundCloud：

- **标题**和**封面**（500 px 图片）使用上传内容自己的信息。
- **艺人**使用 SoundCloud 标注的艺人；如果没有，则使用上传账号名称。若 SoundCloud 标明艺人身份，唱片公司上传的歌曲也会署名给对应艺人。
- **专辑**默认使用曲目名称（视为单曲），除非 SoundCloud 指定了专辑。
- **年份**和**流派**来自发行日期（或上传日期）以及流派标签。

### 音频来源

SoundCloud 链接指向特定曲目，启用 **SoundCloud** 来源时会直接下载该曲目，不进行搜索。它仍遵循来源顺序，与粘贴 YouTube 链接类似：会先尝试排在 SoundCloud 前面的来源（slskd、Deemix）；如果关闭 SoundCloud，则会改为搜索其他启用的来源。如果都找不到，队列会提示：*Could not find … — turn SoundCloud on in Settings > Audio sources to download SoundCloud tracks*。

## 在 SoundCloud 上查找歌曲

对于其他链接中的歌曲，启用 **SoundCloud** 来源后会搜索“艺人 标题”，且仅在满足以下条件时采用搜索结果：

- 上传者名称或标题中包含该艺人（例如 `Artist - Title` 格式的上传也算匹配）；
- 标题与歌曲接近；
- 时长与歌曲相差不超过 30 秒或 20%；
- 结果不是混音、现场录音、盗版、混搭、翻唱、卡拉 OK、加速/减速版本、预览或片段，除非原曲本身就是这种版本。

没有符合条件的结果时，会继续尝试下一个来源。

## 为下载失败的歌曲指定 SoundCloud 链接

在 **Queue** 中，失败歌曲下方的 **Force audio source** 也接受 SoundCloud 曲目链接。歌曲继续保留原来的标题、艺人、专辑、封面和歌词，音频则来自该 SoundCloud 曲目。该链接会在来源列表轮到 SoundCloud 时使用，因此必须先启用 SoundCloud。

[替换音频](replace-audio.md)也接受 SoundCloud 曲目链接，可将媒体库文件替换为 SoundCloud 上传的音频。

## 限制

- **音质**：SoundCloud 提供有损音频串流（通常为 128–160 kbps）。在[下载设置](download-settings.md)中选择 FLAC 或更高比特率会对其重新编码，但无法恢复串流中没有的信息。
- **SoundCloud Go+ 曲目**：没有 Go+ 订阅时，SoundCloud 只提供这类曲目的 30 秒预览。Downtify 会拒绝预览，不会把它保存为完整歌曲；下载会提示 *only streams a 30-second preview on SoundCloud*。
- **地区限制**：上传者在服务器所在国家/地区屏蔽的曲目会像不可用视频一样下载失败。
- **不支持监控**：SoundCloud 链接只对应一首曲目，没有可供[播放列表监控](playlist-monitor.md)的列表。
