---
icon: lucide/star
---

# 热门歌曲

有些艺人的曲库很庞大，真正想听的可能只有几首。与其逐首复制链接，或下载包含 50 多首歌曲的“This is…”播放列表再从中挑选，不如粘贴艺人自己的链接，然后从其热门歌曲中选择。

## 使用方法

1. 将艺人链接粘贴到搜索框或 Home 页面：
   - **Spotify**：`https://open.spotify.com/artist/…`
   - **YouTube Music**：`https://music.youtube.com/channel/UC…` 或 `https://music.youtube.com/@handle`
   - **Deezer**：`https://www.deezer.com/artist/…`
2. **艺人页面**会显示其照片和名称，并列出发行作品（来源有提供时会包含专辑、单曲、EP 和合辑）。Spotify 和 Deezer 的作品按从新到旧排列；点击作品可查看曲目或下载。Spotify 和 YouTube Music 艺人页面的 **Top Songs** 按钮旁还会显示 **Watch for new releases**；Deezer 艺人不显示此项，因为 [Playlist Monitor](playlist-monitor.md) 不支持 Deezer。
3. 点击 **Top Songs** 可按来源的热门程度排序查看歌曲。Spotify 和 YouTube Music 会在眼睛图标徽标中显示播放次数，并按当前语言缩写（葡萄牙语 `1,5 bi`，英语 `1.5B`）；Spotify 使用绿色，YouTube Music 使用红色。YouTube Music 仅报告取整后的数值（如 `1.2B plays`），因此属于近似值；Downtify 会从列出歌曲的同一次 YouTube Music 请求以及额外一次播放次数请求中读取数据。Deezer 的热门排序没有公开播放次数，因此不会显示徽标。前五首默认已勾选；可继续勾选或取消勾选，然后点击 **Download selected**。

### 下载前试听歌曲

在 Top Songs 页面，以及粘贴**专辑**或**播放列表**链接后打开的页面，每首歌曲都可以完整试听：将鼠标悬停在歌曲行上，编号会变成播放按钮（手机上始终显示播放按钮）；点击后歌曲会从 YouTube 串流到内置播放器。再次点击可暂停，点击另一行的按钮则切换歌曲。如果歌曲已在媒体库中，则会从媒体库播放，并在其后排入列表中其他已下载歌曲。

串流由服务器提供，浏览器不会直接连接 YouTube：页面会解析对应 YouTube 视频（YouTube Music 歌曲使用其自身视频，否则使用最接近的搜索匹配结果），服务器将音频下载一次并放入串流缓存，然后播放缓存文件（参见 [`GET /api/stream/file`](../api-reference.md#get-apistreamfile)）。只有服务器需要能够访问 YouTube；年龄限制曲目与下载一样需要配置 YouTube cookies（参见 [YouTube Cookies](youtube-cookies.md)）。

## 来源

| 来源 | “热门歌曲”的定义 | 列出的歌曲 |
|--------|------------------------|--------------|
| Spotify | 艺人自己的 **Popular** 区域，即其 Spotify 页面顶部显示的歌曲 | 最多 10 首 |
| YouTube Music | 按热门程度排序的艺人 **Top songs** 播放列表 | 前 50 首 |
| Deezer | 艺人自己的 **top** 排名，与 `deezer.com` 艺人页面显示的相同 | 前 50 首 |

Spotify 的公开 embed 不提供作品目录，因此 Downtify 会从 Spotify 网页播放器的作品目录查询读取发行信息；该查询也是读取专辑名称时使用的非公开 API。如果 Spotify 更改接口，Downtify 会退回较短列表（所有专辑以及最近的 10 张单曲）；再失败时则不显示发行作品。Spotify 歌曲仍按常规流程先获取元数据再匹配音频，并提前附上专辑名；下载时会像其他 Spotify 歌曲一样补全曲目编号和年份。YouTube Music 歌曲会固定使用其自身视频，与其他 YouTube Music 链接相同。Deezer 提供公开的作品目录接口，因此无需回退；其歌曲采用与 Spotify 相同的元数据和音频匹配流程，如果 Deezer 有提供，还会附上 30 秒试听片段。

## 艺人的 Library 页面

Downtify 在 Spotify 上识别出的艺人（参见[艺人照片、横幅和简介](artist-images.md)）的 Library 页面中，也会在 Tracks 和 Fans also like 旁显示 **Top songs** 标签页。该页以简洁列表列出 Spotify 热门歌曲中的前 **5** 首，列标题为（#、Title、Album、length），行中包含编号、封面、标题、艺人、专辑和时长。尚未下载的歌曲右侧会显示**下载**按钮，并在下载时显示进度；下载完成后按钮变为 **In library**，歌曲可像专辑页面中的曲目一样播放：悬停时编号变为播放按钮，点击封面、双击或轻触均可播放。播放一首歌曲时，列表中其他已下载曲目会按排名顺序排在其后，当前歌曲会突出显示。尚未下载的歌曲可以**完整串流**：悬停时，编号位置会出现播放按钮，点击按钮或封面即可在内置播放器中播放，方式与已下载歌曲相同（参见[下载前试听歌曲](#playing-songs-before-downloading)）。列表下方的 **See more popular songs** 会在前述 Top Songs 页面中打开该艺人；歌曲选择、**Create playlist** 开关和批量下载均在该页面操作。只有识别出艺人的 Spotify ID 后才会显示此标签；首次打开艺人页面时就会获取歌曲，因此无论你当时是否停留在此页，几秒后标签中的数量都会自动填入。

读取歌曲封面、专辑和播放次数需要几秒钟，因此 Downtify 会在首次打开艺人页面时于后台生成每位艺人一个缓存文件：`<downloads>/.metadata/ArtistTopSongs/<Artist>.topsongs.json`。缓存有效期为 **7 天**：打开标签页时会立即读取文件；文件过期后会先显示旧列表，同时在后台获取最新内容，几秒内页面会自动更新，不会打断正在下载或播放的歌曲。文件只包含歌曲信息、封面图、片段链接和播放次数，不含音频或图片文件，也不记录歌曲是否在媒体库中（该状态会实时查询）。这是缓存，可随时删除，之后会重新生成。

## 创建播放列表

首次打开某位艺人的 Top Songs 页面时，**Create playlist** 开关默认**关闭**；如果媒体库中已存在名为 **Top Songs of {artist}** 的播放列表，则默认**开启**，以便后续下载继续添加到该列表。开关状态在当前页面期间会保留。关闭时，歌曲像普通单曲一样直接下载到下载目录；如果启用了[文件整理](file-organization.md)，则会进入艺人/专辑目录，不会创建专属文件夹、M3U 或艺人照片。

开启后，Downtify 会将这些歌曲作为名为 **Top Songs of {artist}** 的播放列表处理。文件位置取决于文件整理设置：

| 按艺人/专辑整理 | 歌曲 | M3U 和封面 |
|---|---|---|
| 两项均关闭 | 放在名为 `Top Songs of {artist}` 的文件夹中 | 同一文件夹中 |
| 任一项或两项开启 | 按设置放入 `<Artist>/`、`<Album>/` 或 `<Artist>/<Album>/`。不会创建 `Top Songs of {artist}` 文件夹。 | 放在 `Playlists/` 中，文件名为 `Top Songs of {artist}.m3u` 和 `.jpg` |

两种情况下：

- [M3U 播放列表](m3u-export.md)中的歌曲均按**艺人排名顺序**排列，即使只选择了其中部分歌曲也一样。
- 如果启用了 **Save playlist cover art**，艺人照片会与 M3U 一起保存并作为封面（参见[播放列表封面](playlist-cover-art.md)）。此功能没有单独设置。

## 已知限制

::: warning 混合使用同一艺人的 Spotify 和 YouTube Music 来源
**Top Songs of {artist}** 的 M3U 文件通过[播放列表目录](library-catalog.md)保持同步，该目录使用 Spotify 曲目 ID 作为键。如果先从 **Spotify** 下载艺人热门歌曲，之后又从 **YouTube Music** 下载（或反过来），第二批文件会正确下载，但下一次刷新 M3U 时会将它们从播放列表文件中移除，因为 YouTube Music ID 不符合该格式。同一来源继续添加歌曲不受影响。
:::

::: info Spotify 歌曲的专辑名称
Spotify 艺人页面不会标明歌曲所属专辑。Downtify 会通过读取完整播放列表所用的同一 Spotify player API 获取专辑名称和播放次数：每位艺人会额外请求一次；该请求未列出专辑时，还会对每张专辑各请求一次。该 API 并非公开接口，因此如果 Spotify 更改接口，Spotify 歌曲的 **Album** 列会为空，播放次数徽标也会消失。歌曲仍可下载，但 Downtify 必须从 YouTube Music 匹配结果中重新获取专辑信息，而这经常会失败，导致文件缺少专辑标签；如果启用了[按专辑整理](file-organization.md)，歌曲还会被放入 `unknown` 专辑文件夹。YouTube Music 热门歌曲已包含专辑信息。任一来源的播放次数无法获取时，都只会隐藏徽标。
:::

## API

参见 API 参考中的 [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl)。
