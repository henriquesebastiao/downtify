---
icon: lucide/users-round
---

# 协作播放列表

你与[指定用户共享的播放列表](users.md#sharing-playlists)对他们是只读的：他们可以播放、关注并保存副本。对于在 Library 中创建的播放列表（使用 **New playlist** 创建，或从源[分离](library-catalog.md#detach-an-imported-playlist)而来），你还可以允许其中部分用户添加和移除歌曲，例如让全家一起编辑派对歌单。这些用户将成为该列表的**编辑者**；其他人仍然只能收听。

## 允许用户编辑

1. 打开播放列表，在页面或其 **⋯** 菜单中选择 **Share…**。
2. 选择 **Specific people**，勾选要共享的用户。
3. 在所选用户下方，为需要编辑列表的用户勾选 **Can add and remove songs**，然后点击 **Save**。

再次打开 **Share…** 可查看编辑者并进行调整。

## 编辑者可以执行的操作

播放列表会显示在他们的 **Shared with me** 下，页面会注明所有者以及他们可以添加和移除歌曲。编辑者可以：

- 在播放列表页面或其 **⋯** 菜单中 **Add songs**；也可以在任意歌曲的菜单中选择 **Add to playlist**，然后在自己创建的播放列表之后选择该列表。
- 在播放列表页面中的歌曲 **⋯** 菜单选择 **Remove from playlist**。
- 选择 **Reorder** 调整歌曲顺序，或再次添加列表中已有的歌曲；参见[播放列表顺序与重复歌曲](playlist-order.md)。

重命名、共享、删除，以及从源链接保存的封面仍由所有者和管理员管理。编辑者仍可像普通查看者一样 **Save a copy**。

以下规则适用于所有编辑者，包括所有者：

- **只能添加他们有权查看的歌曲。** 歌曲来自共享媒体库；管理员[对用户隐藏](users.md#hiding-from-users)的歌曲，无法由看不到它的用户添加。
- **更改会即时显示**给所有者和其他编辑者，无需刷新页面。
- **不会丢失任何人的修改。** 两个人同时添加歌曲时，两人的更改都会保留，并依次应用。

## 何时停止编辑权限

编辑权限随共享设置生效：

- 取消某人的 **Can add and remove songs** 后，该用户将只能收听；将其从共享名单移除则会完全取消其对播放列表的访问。
- 将播放列表设为 **Private** 或 **Public** 会结束所有编辑权限；公开播放列表对所有人均为只读。
- 管理员关闭 **Settings › Library › Allow users to share playlists** 后，用户不能编辑不属于自己的播放列表。与共享权限一样，重新启用后编辑者权限会恢复。
- 重命名播放列表不会移除编辑者；删除播放列表或编辑者账户则会移除相关权限。

## 已导入的播放列表

通过 Spotify、YouTube Music 或 Deezer 链接下载的播放列表仍会跟随其来源：监控或重新下载链接时会重写列表，因此不能设置编辑者。若要共同维护列表：

- **共享可编辑副本**：在 **Share…** 中选择 **Specific people**，系统会保存一份归你所有的副本，并打开共享设置。你选中的用户默认都可以添加和移除歌曲；取消只需要收听的用户，再点击 **Save**。原始列表仍会跟随其来源。
- **从源分离**：将该播放列表本身转为 Library 列表，使它不再跟随来源；之后即可添加编辑者。

## 面向应用和脚本

来自 [`GET /playlists`](../api-reference.md#get-playlists) 和 [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) 的播放列表行包含 `can_edit_tracks`，所有者的行还会列出 `editors`（用户名）。[`PUT /api/library/playlists/visibility`](../api-reference.md#put-apilibraryplaylistsvisibility) 接收 `editors`（必须是 `shared_with` 的子集）；省略该字段会保留仍在共享名单中的现有编辑者。编辑者和所有者一样，可通过 [`POST /api/library/playlists/tracks`](../api-reference.md#post-apilibraryplayliststracks) 修改歌曲。
