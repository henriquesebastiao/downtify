---
icon: lucide/import
---

# 导入媒体库（CSV）

如果你已从其他服务导出媒体库，可导入 CSV 文件并一次性将所有曲目加入下载队列，无需逐首重新添加。

## 支持的导出工具

| 工具 | 说明 |
|------|-------|
| [Soundiiz](https://soundiiz.com/) | |
| [TuneMyMusic](https://www.tunemymusic.com/) | |
| [Exportify](https://github.com/watsonbox/exportify) | |

Downtify 不会针对某一种工具的固定列结构进行硬编码，而是将 CSV 首行的列名（不区分大小写）与一组已知别名匹配。例如，标题列可以是 `Title`、`Track`、`Track Title`、`Track Name`、`Song` 等；艺人列可以是 `Artist`、`Artists`、`Artist Name`、`Artist Name(s)` 等；专辑列可以是 `Album`、`Album Name`、`Album Title` 等。因此，以上工具导出的文件以及使用相同列名手动制作的 CSV 都无需重命名列即可导入。

标题和艺人是必填项。若存在专辑列，Downtify 会读取其值并将专辑名称用于队列、匹配和文件标签。其他导出列（如 ISRC、Spotify track URI 和时长）会被忽略。每一行都像自由文本搜索一样，通过 YouTube Music 解析。

## 导入方法

1. 在首页搜索框下方点击 **Import a library CSV**。
2. 选择导出的 `.csv` 文件。

文件完全在浏览器中读取，并以纯文本发送到服务器，不会上传到其他位置。Downtify 会解析文件、将识别出的行加入队列，然后打开 Download Queue 页面。进度通过 WebSocket 实时推送，与其他批量下载相同。

导入批次使用文件名命名（去掉 `.csv` 扩展名）；与其他播放列表下载一样，如果启用了相关设置，也会生成 [M3U 文件](m3u-export.md)。

## 限制和错误处理

- 每个文件最多 **2,000 行**。较大的导出文件请拆分后导入。
- 缺少标题或艺人的行会被直接跳过。专辑列缺失或单元格为空均可；YouTube Music 之后可能会补全专辑信息。
- 一个单元格中的多个艺人（以 `,` 或 `;` 分隔）会拆分为列表。
- 如果标题列或艺人列无法识别，导入会立即拒绝，并提示检测到的列名；不会将任何内容加入队列。

## 避免触发速率限制

大批量导入会在短时间内产生大量 YouTube Music 搜索和下载请求，容易触发速率限制。导入大型文件前，可考虑降低[并行下载数](download-settings.md#parallel-downloads)，并在设置中启用[下载间隔](download-settings.md#delay-between-downloads)。

## API

底层接口说明请参阅 API 参考中的 [`POST /api/download/csv`](../api-reference.md#post-apidownloadcsv)。
