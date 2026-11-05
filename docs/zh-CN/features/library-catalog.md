---
icon: lucide/library
---

# 媒体库目录与路径同步

Downtify 会为 `/downloads` 中的文件维护一个小型**目录**（还包括[保留原位的 slskd 文件](slskd-navidrome.md#leave-files-in-place)，以及你在设置中添加的[额外文件夹](external-library.md)），确保移动文件或播放列表内容变化后，媒体库页面、播放器、M3U 导出、Navidrome 同步和重复检测仍能保持一致。

## 存储内容

| 存储项 | 位置 | 用途 |
|-------|---------|---------|
| **曲目索引** | `/data/downtify_library.db` | 将 Spotify 曲目 ID 映射到媒体库路径，以便识别磁盘上已有的歌曲 |
| **播放列表目录** | `/data/downtify_library.db` | 记录每个已下载 Spotify 播放列表包含的曲目 |
| **播放列表下载记录** | `/data/downtify_library.db` | 跟踪 Spotify 播放列表下载，并缓存其 Spotify 曲目列表 |
| **Navidrome 索引** | `/data/downtify_library.db` | 记录每个文件对应的 Navidrome 歌曲 ID |
| **媒体库元数据缓存** | `/data/downtify_library.db` | 为 `GET /tracks` 缓存每个文件的标题、艺人、所有署名艺人、专辑、专辑艺人、曲目编号、年份、完整发行日期、时长和封面尺寸；仅当文件修改时间或大小变化时重新读取 |
| **升级任务** | `/data/downtify_library.db` | 保存[媒体库升级](library-upgrade.md)队列和每首曲目的上次检查时间，以便重启后继续任务 |
| **路径扫描缓存** | 内存，以及 `/data/downtify_library.db` 中的快照 | 保存整理后的 `GET /tracks` 行、播放列表清单和路径对应关系。界面路由直接使用快照，无需遍历磁盘。每次下载完成都会**立即合并到快照**（新艺人无需等待就会显示）；删除文件也会**立即从快照移除**（专辑无需等待就会从网格消失）。下载队列空闲数秒后会在后台完整遍历目录树，而不是按固定周期扫描。`GET /list?refresh=true` 会丢弃快照并立即重新扫描。 |
| **隐藏条目** | `/data/downtify_library.db` | 管理员[对用户隐藏的](users.md#hiding-from-users)歌曲、专辑和艺人 |
| **封面缓存** | `/data/cover_cache`（可选） | 缓存从文件中提取、供 `GET /cover` 使用的封面图片 |

文件移动后通过**内容键**匹配：内容键是根据文件名和大小计算的哈希值。将文件移到其他目录不会改变内容键；替换成不同文件则会生成新的内容键。

## Settings → Library

### 在磁盘缓存封面

启用后，Downtify 会将提取出的封面保存在 `/data/cover_cache`，因此媒体库和播放器无需为每张缩略图重复读取标签。可随时关闭；影响仅是磁盘空间占用。

### 修复媒体库路径

在 Downtify 外部**移动或重命名文件**，或手动删除文件后，使用此功能：

1. 打开 **Settings → Library → Fix library paths**。
2. Downtify 会扫描媒体库文件夹，并执行以下操作：
   - 如果文件不在原路径，但在其他位置找到具有相同内容键的文件，则**更新**曲目索引和播放列表目录中的路径；
   - **移除**已不存在文件的过期记录；
   - **索引**内容键功能加入前保存的旧记录；
   - 将[已点赞歌曲](liked-songs.md#keeping-likes-in-step-with-the-files)对应到文件的新位置。
3. 如果启用了 **Generate M3U** 和/或 **Create playlists in Navidrome**，受影响的播放列表会重新生成。

只有点击按钮（或调用 `POST /api/library/reconcile`）时才会执行，不会定期自动运行。

### 现有音乐文件夹

如需播放 Downtify 未下载的收藏，请在 **Settings → Library** 添加文件夹并点击 **Sync folders**。文件仍保留在磁盘原位；Downtify 会读取标签并匹配艺人。详见[现有音乐文件夹](external-library.md)。

::: warning
重写播放列表时，如果媒体库文件的标签明显与其登记的 Spotify 曲目不符，该文件会被删除。详见 [slskd 与 Navidrome](slskd-navidrome.md#playlist-sync)。
:::

::: info 删除与移动
在 **Library** 页面删除曲目时，目录已经会清理相关记录，并在后台重写受影响的 M3U 文件和 Navidrome 播放列表，因此之后无需再修复。
:::

## 媒体库页面

媒体库页面包含四个标签页：**Albums**、**Artists**、**Playlists** 和 **Tracks**：

- **专辑、艺人和播放列表**可显示为封面网格或紧凑列表（会记住视图选择），并支持文本筛选以及按最近添加、名称、艺人、年份或曲目数排序。专辑和艺人根据各文件标签（专辑艺人、专辑、年份）构建，与磁盘目录结构无关。带有 compilation 标记且专辑艺人为 `Various Artists` 的合辑会在 Albums 中显示为一个专辑，而曲目仍归入各自艺人页面。旧版本可能会把多艺人歌曲（包括 `Zé Neto & Cristiano` 这样的组合）都标成 `Various Artists`；没有合辑标记的此类曲目现在会按第一位艺人归组。未填写专辑标签的歌曲会显示在 Tracks 和对应艺人页面中，不会出现在 Albums 中。
- **艺人**会列出曲目关联的所有艺人：专辑艺人；如果是合辑或文件没有专辑艺人，则显示第一位艺人。艺人页面还会列出其作为客串参与的歌曲，并标记为 **Guest**；Albums 标签页只显示该艺人自己的专辑，没有专辑时会隐藏该标签。只作为其他艺人署名一部分出现的名字不会单独创建页面：标签可能会将组合成员逐一记录（例如 `Henrique; Juliano`，这是 YouTube Music 对某些组合的署名方式，旧版 Downtify 也会这样写），为成员分别建立页面会错误地显示不存在的艺人。**Various Artists** 不会单独列出：合辑歌曲归在各自艺人页面，专辑则保留在 Albums 中。
- 曲目列表、Now playing 页面、Finder 和热门歌曲行中，艺人名称会链接到对应媒体库艺人页面；若媒体库中没有该艺人，则链接到搜索结果。类似地，专辑名称会链接到媒体库专辑页面或相关搜索结果。Discover 和 Finder 不会跳转到 Search：媒体库中不存在的艺人或专辑只显示为普通文字。艺人名称优先读取文件的 `ARTISTS` 标签（参见[多位艺人与合辑](file-organization.md#several-artists-and-compilations)），因此 *Earth, Wind & Fire* 这样的名称不会因逗号被拆开。没有该标签时，除非艺人文字与专辑艺人相同，或拆分后的名称组成该专辑艺人（例如艺人标签为 `Henrique; Juliano`，专辑艺人为 `Henrique, Juliano`），否则会按 `;`、` / `或`, `分隔拆分。
- **播放列表**包括带有 [M3U 文件](m3u-export.md)的已下载播放列表、通过 **New playlist** 创建的可编辑播放列表，以及尚无 M3U 文件但已跟踪的[播放列表下载](slskd-navidrome.md#playlist-downloads)。导入的 Spotify/YouTube 播放列表在[脱离来源](#detach-an-imported-playlist)前为只读。其他人[分享给你](users.md#sharing-playlists)的播放列表会列在网格下方，与自己的播放列表分开。添加[已点赞歌曲](liked-songs.md)后，*Liked songs* 会置顶。自己创建的播放列表使用最多四张曲目封面拼成的图；导入的播放列表则保留 M3U 中保存的封面。
- **Tracks** 是可排序的表格，列出标题、专辑、格式、添加日期和时长，并提供文本筛选、格式筛选和复选框。点击一行后，再按住 Shift 点击另一行可选择一个范围。点击列标题可排序；也可使用表格上方的 **Sort by** 菜单（手机上列标题隐藏，只能使用此菜单）。排序方式包括最近添加或最早添加、标题/艺人/专辑升序或降序、时长从长到短或从短到长。排序选择会被记住。

宽屏下，**Tracks** 表格还会显示可排序的 **Release date** 列。日期取自音频标签；只有年份的文件只显示年份。所有屏幕尺寸都可在 **Sort by** 菜单中选择按发行日期从新到旧或从旧到新排序。

播放列表歌曲也有相同的 **Sort by** 菜单，并增加了 **Playlist order**（播放列表原始顺序，也是默认顺序）；也可以点击列标题排序。**Play** 和歌曲列表会遵循所选顺序，每个播放列表的选择都会被记住。

打开专辑、艺人或播放列表后，可查看曲目并使用 **Play**、**Shuffle** 和 **Add to queue**。播放列表页面提供 **Download as ZIP** 按钮；专辑页面可在 **⋯** 菜单中找到此操作。自己创建的播放列表还提供 **Add songs**、**Rename** 和 **Share…**（参见[共享播放列表](users.md#sharing-playlists)）；导入的播放列表提供 **Share…** 和 **Detach from source**（见下文）。已下载播放列表页面会显示已下载曲目数量，并可通过 **Missing** 筛选器查看尚未下载的曲目、使用 **Download missing** 下载，以及选择 **Watch for new tracks**。**Delete playlist** 位于 **⋯** 菜单中：删除导入播放列表会删除音频；删除自己创建的播放列表只会移除播放列表本身。

### 搜索播放列表

长播放列表只会在页面中渲染当前可见的歌曲，因此浏览器自带的查找功能（`Ctrl` + `F`）无法搜索其余曲目。歌曲列表上方的 **Search this playlist** 输入框会搜索整份列表，包括标题、艺人、专辑和文件名，且忽略大小写和重音符号。在播放列表页面按 `Ctrl` / `⌘` + `F` 会将焦点移到此输入框；再次在输入框中按该组合键会打开浏览器查找。按 `Esc` 可清除搜索。

旁边的筛选器可进一步缩小列表范围。每个筛选器显示其歌曲数量，且仅在有歌曲时出现：

| 筛选器 | 显示内容 |
|--------|-------|
| **All** | 播放列表中所有已下载的歌曲 |
| **Missing** | 源播放列表中尚未进入媒体库的歌曲（Spotify 播放列表下载）；选择此项时会从 Spotify 查询 |
| **Failed** | 已查询 **Missing** 后，下载失败的缺失歌曲；每首歌曲都有重试按钮 |
| **YouTube Music**、**Soulseek (slskd)**、**Deemix**… | 由该来源获取的歌曲。Downtify 会记录新下载歌曲的来源；旧歌曲会标记为 **Unknown source**，保留在原位置的 slskd 文件和来自自有文件夹的歌曲除外 |
| **Not in Navidrome** | 启用 [Navidrome 同步](slskd-navidrome.md)时，尚未匹配到 Navidrome 歌曲的曲目 |

搜索和筛选器可以同时使用；它们下方会显示当前结果数量。每首歌曲保留其在播放列表中的编号，排序、播放和歌曲菜单操作都会针对当前显示的结果执行。

已下载的 Spotify 播放列表还提供 **Playlist diagnostics** 面板。点击 **Check** 可比较缓存的 Spotify 曲目列表、播放列表目录、磁盘文件、TrackIndex、当前用户的 Monitor 历史和已同步的 Navidrome 播放列表。选择任意统计数量，可查看对应的曲目或文件。只有主动请求时才会检查 Navidrome；历史记录或 Navidrome 数据不可用时会显示“不可用”，不会显示为零。管理员隐藏的曲目不会展示给其他用户。

### 脱离导入的播放列表

从 Spotify 或 YouTube Music 链接导入的播放列表会与来源保持同步，因此不能直接编辑。若需整理播放列表（例如移除不相关歌曲或添加遗漏歌曲），请打开播放列表并选择 **Detach from source**。它会变成本地创建的播放列表，保留原有歌曲和所有者，并提供 **Add songs**、**Rename** 和移除歌曲等操作。代价是断开来源链接：播放列表不再从 Spotify 或 YouTube Music 更新；如果设置了 [Playlist Monitor](playlist-monitor.md) 监控，也会移除对应监控，并停止跟踪“缺失歌曲”。已下载歌曲不会受影响；原封面会保留到首次编辑，此后改为使用曲目封面拼图。在应用中无法撤销脱离操作；再次下载该链接会创建一个新的导入播放列表。

所有账号看到的媒体库相同，但管理员[对用户隐藏的内容](users.md#hiding-from-users)会对普通用户隐藏；管理员可以看到全部内容，隐藏项会显示划线眼睛图标。管理员可从歌曲、专辑或艺人的 `…` 菜单，或 Tracks 页面的选择工具栏中隐藏和恢复项目。

**Download as ZIP** 会将选中曲目打包为一个 ZIP 文件并下载到当前浏览设备，同时保留目录结构。Downtify 运行在家庭服务器上时，可用此功能将一批曲目保存到本地。可配合 **Select all** 下载当前筛选器显示的全部歌曲。压缩包在传输过程中生成，不会写入服务器磁盘；每次最多可下载 2000 首曲目。

## API

| 方法 | 路径 | 说明 |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | 获取媒体库路径并绕过路径扫描缓存 |
| `GET` | `/api/library/summary` | 获取首页统计和最近专辑，不返回完整曲目列表 |
| `GET` | `/api/library/albums` | 获取专辑卡片（数量和封面文件），不返回所有曲目 |
| `GET` | `/api/library/artists` | 获取艺人卡片（数量和封面文件），供 Library 和 Discover 使用 |
| `GET` `POST` | `/api/library/visibility` | 管理员接口：查看对用户隐藏的内容，以及隐藏/恢复条目 |
| `POST` | `/api/library/lookup` | 获取媒体库行，用于搜索/链接中已下载歌曲的匹配 |
| `GET` | `/tracks` | 获取带标签的媒体库曲目。`?playlist=`、`?artist=`、`?album=`、`?q=` 和 `?limit=` 可返回子集 |
| `GET` | `/media/{path}` | 提供媒体库文件，包括 `slskd/…` 和 `ext/…` 路径 |
| `GET` | `/playlist-cover?file=…` | 提供播放列表专属[封面](playlist-cover-art.md)，`/playlists` 中以 `cover` 字段报告 |
| `POST` | `/api/library/archive` | 为选定曲目准备 ZIP 文件（返回一次性 ticket） |
| `GET` | `/api/library/archive/{token}` | 向浏览器传输 ZIP 文件 |
| `DELETE` | `/api/library/playlist?playlist_name=…` | 删除导入播放列表的音轨、M3U 和目录记录；若为自建播放列表，则只删除 M3U |
| `POST` | `/api/library/playlists` | 创建空白的可编辑播放列表 |
| `POST` | `/api/library/playlists/tracks` | 在自建播放列表中添加或移除媒体库文件 |
| `POST` | `/api/library/playlists/rename` | 重命名自建播放列表 |
| `PUT` | `/api/library/playlists/visibility` | 以只读方式[共享播放列表](users.md#sharing-playlists) |
| `POST` | `/api/library/playlists/copy` | 将可访问的播放列表保存为自己可编辑的副本 |
| `POST` | `/api/library/playlists/detach` | 将导入的播放列表转换为可编辑播放列表 |
| `POST` | `/api/library/reconcile` | 修复媒体库路径，然后刷新 M3U/Navidrome 播放列表 |
| `POST` | `/api/library/external/sync` | 在后台扫描额外音乐文件夹 |
| `GET` | `/api/library/external/sync` | 获取正在运行的额外文件夹同步任务或最近一次完成日志 |
| `POST` | `/api/library/external/unmap` | 从媒体库中移除额外文件夹映射，但不删除音频 |
| `GET`/`POST` | `/api/library/upgrade…` | 扫描并修复已下载内容，参见[升级媒体库](library-upgrade.md#api) |

请求和响应结构请参阅[API 参考](../api-reference.md#library)。
