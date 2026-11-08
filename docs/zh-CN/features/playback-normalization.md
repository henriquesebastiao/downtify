---
icon: lucide/audio-lines
---

# 音量标准化

歌曲来源不同，母带处理响度也各异，因此相邻歌曲的音量可能相差很大。**音量标准化**会让歌曲以接近的响度播放。此功能默认关闭，不会修改音频文件：服务器只负责测量，播放器会在播放时调高或调低音量。

## 启用标准化

在 Web 应用中打开 **Settings → General**（`/settings`），在 **Volume normalization** 分组中启用 **Normalize playback volume**。此选择仅属于你的账号，会跟随账号在其他浏览器中生效，不会影响其他用户。

启用后，**Playback level** 提供 **Normal**、**Louder** 和 **Maximum** 三个选项。此选项保存在当前浏览器中，与手机上的选择相互独立。Normal 使用现有目标响度；其他选项会在每首歌曲测得的峰值限制内提高目标。播放中调整时，音量会平滑变化，无需等待下一首曲目或重新分析。因此，如果某首歌的峰值余量较小，Louder 和 Maximum 听起来可能相近。

歌曲播放时，开关下方会显示对其应用的处理：

| 提示 | 含义 |
|---------|---------|
| 已将测量音量应用于当前歌曲。 | 曲目已有测量结果，正在按标准化音量播放 |
| 尚无此歌曲的测量结果：保留原始音量。 | 尚未分析，或文件发生过变化；参见[分析媒体库](#analyzing-the-library) |
| 歌曲静音：保留原始音量。 | 没有足够响度可供测量 |
| 标准化不可用：保留原始音量。 | 浏览器不支持 Web Audio，或服务器未能及时响应 |

播放过程中启用标准化会立即对当前歌曲生效，并进行短暂淡入。媒体库之外的歌曲（预览曲目和未下载歌曲的串流）始终保持原始音量。

Android 应用也有自己的开关：**Settings → Playback → Normalize volume**。设置从下一首歌开始生效，并使用相同测量结果；如果歌曲下载到手机时服务器已完成测量，离线副本也适用。

## 音量级别的计算方式

每首歌曲从头到尾应用一个固定增益；不会进行压缩，歌曲内部安静和响亮片段之间的相对差异保持不变：

- 目标综合响度为 **-18 LUFS**（Normal）、**-12 LUFS**（Louder）和 **-6 LUFS**（Maximum）；实际峰值限制可能使歌曲低于所选目标。
- 安静歌曲最多提高 **12 dB**。
- 增益不会让峰值超过 **-1 dBTP**，避免削波。峰值按重采样到 192 kHz 的音频测量，也能捕获采样点之间的峰值。

因此，特别安静或动态范围较大的歌曲可能达不到目标响度。Web 播放器会将增益与[均衡器](player.md#equalizer)一起应用；两者都使用 Web Audio API，并受到相同的[浏览器限制](player.md#browser-support)：在 iPhone 或 iPad 上，启用其中任意一项时锁屏播放可能会停止。

## 分析媒体库

测量时需要完整读取每首歌曲，因此只有管理员主动要求时才会执行。管理员可在 **Volume normalization** 分组中看到分析控制：

- **Analyze library**：将媒体库中的所有歌曲加入队列。有效测量结果会跳过，因此之后（例如新增下载后）再次运行时，只会测量新增、移动、替换或更改过的歌曲，以及之前失败的歌曲。
- **Pause analysis**：等待当前测量完成后暂停。**Resume analysis** 会从中断处继续。
- 计数器会显示已分析和失败的歌曲数。无法由 FFmpeg 解码，或读取期间发生变化的文件会计为失败。

分析在后台以低优先级运行 FFmpeg：最多同时处理两首歌曲；容器 CPU 少于两个时会进一步降低并行数（遵循 CPU 配额和亲和性设置），且每个任务只使用一个线程。分析不会自行启动，包括重启后也不会；中断的任务会保留，等待点击 **Resume analysis**。

测量结果与测量时的文件状态绑定（大小、修改时间和 inode）。如果文件被替换或重写（例如通过[媒体库升级](library-upgrade.md)、[替换音频](replace-audio.md)或手动操作），旧测量就不再适用，歌曲会以原始音量播放，并在下次点击 **Analyze library** 时重新测量。

## 开发者信息

Web 应用通过 `GET /api/library/loudness?file=` 获取曲目测量结果；应用使用 `GET /api/v1/tracks/{id}/loudness`。管理员通过 `GET /api/library/loudness/status` 和 `POST /api/library/loudness/{start,pause,resume}` 控制分析。详见[API 参考](../api-reference.md#playback-normalization)和[移动客户端协议](../mobile-client-contract.md)。
