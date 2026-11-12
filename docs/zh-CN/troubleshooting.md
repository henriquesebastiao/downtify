---
icon: lucide/life-buoy
---

# 故障排查

这里列出常见问题及其解决方法。大多数下载失败都与前两项有关。

## 显式内容歌曲无法下载

**现象**：下载失败，队列提示歌曲受年龄限制；旧版本可能显示类似以下原始错误：

```
Error: ERROR: [youtube] <id>: Sign in to confirm your age.
This video may be inappropriate for some users.
```

**原因**：YouTube 只向已登录的成年账号提供受年龄限制（显式内容）的歌曲。Downtify 默认匿名下载，因此 YouTube 会拒绝请求。

**解决方法**：提供 YouTube Cookie：**Settings**（⚙️）→ **YouTube cookies** → **Upload cookies.txt**。导出方法请参阅 [YouTube Cookie](features/youtube-cookies.md)。

配置 Cookie 后仍失败，可能是 Cookie 已过期，或账号尚未完成 Google 年龄验证。请在已通过验证的账号浏览器中重新导出 Cookie 文件并上传。

## 下载失败、超时或始终未开始

**现象**：看似普通的歌曲也下载失败，有时会提示“登录以确认你不是机器人”或出现格式/提取错误。

**原因**：YouTube 会限制流量，并对疑似自动化的请求发起验证。与家庭网络相比，VPS 或 VPN 环境更容易遇到此问题。

**解决方法**（按通常的有效程度排序）：

1. **上传 `cookies.txt`**（[YouTube Cookie](features/youtube-cookies.md)）。经过身份验证的会话较少触发验证，这是最有效的单项措施。
2. **在下载之间增加间隔**：进入 **Settings** → *Delay between downloads*（可先试 5–15 秒），并降低 *Parallel downloads*。一次性并发下载整个播放列表容易触发限流。
3. **强制使用 IPv4**：如果主机启用了 IPv6，但实际无法通过 IPv6 路由（常见表现是 DNS/`EAI_AGAIN` 错误），请设置 `DOWNTIFY_FORCE_IPV4=1`。
4. **更新镜像**：运行 `docker compose pull && docker compose up -d`。YouTube 会频繁调整防护机制，每个新版本都会附带较新的 `yt-dlp`。

## Windows / Docker Desktop 未读取 cookies.txt

**现象**：已设置 `DOWNTIFY_COOKIES_FILE`，但 Downtify 的行为就像没有 Cookie 一样。

**原因**：该变量需要的是*容器内*路径。`C:\Users\me\cookies.txt` 这样的 Windows 路径在容器中无效；必须先将文件绑定挂载到容器，变量才能指向它。

**解决方法**：无需设置该变量，直接通过 **Settings** → **YouTube cookies** 上传文件。此方式不需要挂载文件，在各个平台上的操作都相同。

如果仍想使用该变量，请挂载文件，并将变量设为容器内的挂载路径，而不是主机路径：

```yaml
volumes:
  - ./cookies.txt:/cookies.txt:ro
environment:
  - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

## Cookie 上传按钮呈灰色

已设置 `DOWNTIFY_COOKIES_FILE`，表示此部署由外部管理 Cookie 文件，因此 Web 界面会有意保持只读。删除该变量并重新创建容器后，即可通过界面管理 Cookie。

## 更新容器后，已上传的 Cookie 不见了

上传的文件保存在 Downtify 数据目录（`/data`）。如果该目录没有映射到命名卷或绑定挂载，重新创建容器时其中的所有内容都会丢失，包括设置和播放列表监控数据库：

```yaml
volumes:
  - ./downloads:/downloads
  - downtify_data:/data   # ← keep this
```

## 上传时提示“cookies.txt 无效”

Downtify 会在上传时校验文件。文件必须是 **Netscape** Cookie 格式：每行一条 Cookie，字段以制表符分隔，也可以包含 `#` 注释。JSON 导出文件、电子表格或复制的 `Cookie:` 请求头均不符合要求。

请使用可导出 Netscape 格式的浏览器扩展（参阅 [YouTube Cookie](features/youtube-cookies.md)），并在打开 `youtube.com` 时导出。

## 播放列表重复下载已有歌曲

Downtify 会在数据库中记录所有自动下载的歌曲，因此将文件移到磁盘其他位置不会触发重新下载。只有每小时检查发现下载目录中确实缺少对应文件时，才会重新下载。详见[播放列表监控](features/playlist-monitor.md#how-it-works)。

如果每次重启后文件都会消失，说明 `/downloads` 卷没有持久化，请按上文的方法配置。

## 提示“找不到与‘…’匹配的 YouTube 视频”

YouTube Music 和普通 YouTube 都没有返回通过匹配检查的结果。检查条件包括标题与原曲相似、至少有一位艺人相同、不是卡拉 OK/翻唱/现场/其他语言版本，且时长与 Spotify 版本相差不超过 30 秒。详见[工作原理](how-it-works.md#fallback-to-standard-youtube)。

这通常表示该歌曲确实未上传到 YouTube，或上传时使用了差异很大的标题或艺人署名。如果你能自行找到正确视频，可将其 YouTube 链接粘贴到搜索栏，直接下载该视频。

## 下载的音频标签或封面不正确

Downtify 从 Spotify 获取元数据，并在 YouTube Music 上匹配音频。信息不符通常是因为匹配到了翻唱、混音或现场版本。与搜索结果相比，使用 Spotify **专辑**链接下载能为匹配器提供更多信息（曲目编号、专辑和发行类型）。

## 仍未解决？

请在 [GitHub 问题跟踪页](https://github.com/henriquesebastiao/downtify/issues)提交问题，并附上：

- Downtify 版本（显示在侧边栏底部以及 **Settings → About** 中）；
- 出错时段附近的容器日志（`docker compose logs downtify`）；
- 是否已配置 Cookie。
