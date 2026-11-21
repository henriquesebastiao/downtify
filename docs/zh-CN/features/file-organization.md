---
icon: lucide/file-headphone
---

# 文件整理

新服务器默认按艺人和专辑整理文件（`Artist/Album/…`）：**按艺人整理**和**按专辑整理**均默认开启。关闭两者即可使用下方的平铺布局。此前配置的服务器会保留原选择。

## 平铺布局（两者均关闭）

单曲和 YouTube 搜索下载直接保存在下载文件夹根目录。播放列表和专辑歌曲则保存在各自的子文件夹：

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← single track
```

## 按艺人整理

开启**设置 → 下载与文件 → 按艺人整理**后（默认开启），所有歌曲，包括播放列表和专辑下载，都会归入以专辑艺人命名的子文件夹，参见[多位艺人与合辑](#several-artists-and-compilations)：

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

此结构兼容 Jellyfin、Navidrome、Plex 等媒体服务器，以及 Beets 等要求 `Artist/Song.ext` 文件夹布局的音乐库管理工具。

## 多位艺人与合辑

一首歌曲经常有多位署名艺人。Downtify 会在文件的**艺人**标签中保留所有署名，同时将每位艺人分别写入 **ARTISTS** 标签（MP3 中为 `TXXX:ARTISTS`），因此播放器无需按逗号拆分 `Earth, Wind & Fire` 这样的姓名。不过，文件夹只归一位艺人：使用**专辑艺人**，合辑则使用歌曲的第一位艺人。

- 专辑艺人是来源（Spotify、YouTube Music 或 Deezer）为**专辑**署名的艺人，整张专辑的每首歌曲相同，并写入**专辑艺人**标签。来源未提供时，使用歌曲的第一位艺人。
- 二人组合或乐队视为一位艺人。YouTube Music 有时会按成员逐项署名，例如专辑和各歌曲上的 `Henrique & Juliano` 返回为 `Henrique` 和 `Juliano`，顺序有时还会颠倒，例如返回 `Mateus` 和 `Jorge` 来表示 `Jorge & Mateus`。每个署名都链接到一个 YouTube Music 频道；若某位成员的频道名是由相邻署名组成的完整组合名，Downtify 会将姓名重新合并：文件夹、**专辑艺人**、**艺人**和 **ARTISTS** 标签都使用 `Henrique & Juliano`。真正的合作歌曲中，各艺人使用自己的频道，便会保留全部艺人。若 YouTube Music 没有将任何成员链接到组合频道，姓名仍保持拆分；音乐库不会为始终只与他人共同署名的姓名创建独立页面，参见[音乐库目录](library-catalog.md#library-page)。
- 客串艺人不会改变归属。Michael Jackson 的 *Thriller* 中有客串的 *The Girl Is Mine* 仍保存在 `Michael Jackson/Thriller/`，而 *Lady Marmalade* 单曲（Christina Aguilera、Lil' Kim、Mýa、P!nk）保存在 `Christina Aguilera/`。
- 只有来源本身署名为**群星**的专辑，例如电影原声或“Now That's What I Call…”系列，才视为合辑，除非你[手动标记](#marking-an-album-as-various-artists)。单首 YouTube Music 歌曲不会自动视为合辑：YouTube Music 会将相同音频归入多个发行版本，并可能显示其中任意版本作为专辑，常常是合辑，因此只有整张 YouTube Music 专辑下载才适用。其歌曲会将专辑艺人设为“Various Artists”，并写入合辑标记（MP3 为 `TCMP`，FLAC/Ogg/Opus 为 `COMPILATION`，M4A 为 `cpil`）。Navidrome 等媒体服务器按这些标签而非文件夹归组，因此能保持专辑完整。不过在磁盘上，**按艺人整理**不会创建 `Various Artists` 文件夹，每首歌曲仍放在自己的第一位艺人文件夹下。
- 旧版 Downtify 会将任何多艺人歌曲标记为**群星**，但没有写入合辑标记。音乐库仍像以前一样，将这些歌曲列在第一位艺人的专辑下；**标记为群星专辑**可将专辑设为真正的合辑。

```
downloads/
├── Christina Aguilera/
│   ├── Lady Marmalade/
│   │   └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
│   └── Moulin Rouge/                  ← from the soundtrack (a compilation)
│       └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
└── David Bowie/
    └── Moulin Rouge/                  ← same soundtrack
        └── David Bowie - Nature Boy.mp3
```

单曲版和 *Moulin Rouge* 原声带中的 *Lady Marmalade* 属于两个发行版本，分别归入各自专辑。原声带歌曲分散在各艺人的文件夹中，但都标记为同一张“Various Artists”合辑，因此音乐库和媒体服务器仍会将 *Moulin Rouge* 显示为一张专辑。

### 将专辑标记为群星专辑

来源可能将多位艺人地位相同的发行作品只归给一人，例如 Deezer 将 *Lady Marmalade* 单曲归在 Christina Aguilera 名下。管理员可在音乐库的专辑页面中，点击**添加到队列**旁的**标记为群星专辑**修正。

- 专辑的每首歌曲都会将专辑艺人设为“Various Artists”，并写入合辑标记。文件中的其他内容不变，位置也不变，因为合辑歌曲本来就按各自第一位艺人存放。每个文件都会通过工作副本重写，保留修改时间；若重写失败，原文件保持不变。
- 音乐库的**专辑**中，该专辑会归在**群星**名下，专辑页面也会对应迁移；每首歌曲仍保留在各自艺人的页面中。
- Downtify 会记住该专辑，之后下载其中歌曲时采用相同标签。
- 合辑上的同一按钮显示为**取消群星专辑标记**，撤销标记并恢复原专辑艺人。来源本身标记为合辑的专辑也可取消，此时专辑艺人取多数歌曲的第一位艺人，以后下载该专辑的歌曲也不会再次标记。

只有管理员可见该按钮。媒体服务器会在下次音乐库扫描时识别变化。

## M3U 与艺人文件夹

开启*按艺人整理*并启用 M3U 生成后，下载 Spotify 播放列表时，M3U 会保存在 `<downloads>/Playlists/<playlist-name>.m3u`，而不是播放列表子文件夹中，因为歌曲已分散在多个艺人文件夹下。无论将音乐库挂载到何处，M3U 内的相对路径仍可正确解析。

## 修改设置

设置对所有**新**下载立即生效，不会移动磁盘上已有的文件。

## 删除歌曲时清理空文件夹

从音乐库页面删除歌曲后，若其播放列表、艺人或专辑文件夹变空，也会一并删除；再逐级清理变空的父文件夹，例如最后一张专辑删除后的艺人文件夹，直到下载目录为止，下载目录本身不会删除。仍含有其他歌曲、`.m3u` 或仍在使用的 `cover.jpg` 等内容的文件夹不会改动。

## 同时选择并删除多首歌曲

音乐库歌曲列表为每首歌曲提供复选框，并有**全选**复选框，可选择当前筛选条件下的全部歌曲，参见[音乐库页面](library-catalog.md#library-page)。选择栏中的**从音乐库删除**会通过一次请求删除全部所选歌曲（`DELETE /delete/batch`，参见 [API 参考](../api-reference.md)），并像逐首删除一样清理 `.lrc`、孤立 `cover.jpg` 和空文件夹。

若要删除整张专辑或播放列表，打开后在 **⋯** 菜单中选择**删除**。若要删除某位艺人的所有歌曲，在歌曲列表筛选器中输入艺人姓名，再**全选**并删除。
