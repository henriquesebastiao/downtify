---
title: Deemix
icon: lucide/music
---

# Deemix 音频来源

Deemix 是可选音频来源，默认关闭。在 **Settings → Audio sources** 中的 slskd 下方进行配置，并将其加入来源顺序。你需要拥有兼容的 Deemix 服务器，以及具备所请求音质权限的 Deezer 账号。本功能不提供订阅，也不会绕过订阅限制。

## 凭据和共享文件夹

请保留 Deemix 默认的按会话登录模式。不要在未受保护的服务器上启用 single-user 模式：其连接接口会返回共享 ARL。

将 Deezer ARL 保存在私有文件中并挂载给 Downtify，确保只有 Downtify 服务账号可以读取，然后将 `DOWNTIFY_DEEMIX_ARL_FILE` 设为该路径。只有在打开 Cookie 会话时才会读取 ARL。ARL 不会保存到设置、返回浏览器或写入日志。请像保护密码一样妥善保护它；应私下获取和更换，不要发布到问题跟踪页或聊天中。此集成不会更改 Deemix 的服务器级登录或下载设置。连接测试不会将下载任务加入队列。

| 设置 | 用途 |
| ----------------------------- | ------------------------------------------------------------------ |
| Server URL | Deemix 的内部地址，例如 `http://deemix:6595` |
| Download folder inside Deemix | 通常为 `/downloads` |
| Same folder inside Downtify | 共享 bind mount，例如 `/deemix`；支持只读挂载 |
| Quality | MP3 128、MP3 320 或 FLAC；不具备相应权限时会明确报错 |

保存后，共享文件夹会登记为媒体库额外文件夹。文件会留在 Deemix 的艺人/专辑目录中。Downtify 会保留其格式、标签、封面和 `.lrc` 文件，不会重写它们。播放器会读取已有的嵌入歌词和同名 `.lrc` 文件。此集成不会删除、移动或生成音频及歌词文件。

Deezer 曲目链接会选择指定录音。跨目录下载必须能无歧义地精确匹配艺人/标题，并在提供时匹配专辑和时长。匹配结果有歧义时会回退到下一个已启用来源。Deemix 队列任务完成后，Downtify 还会检查文件、时长和音质。此集成不会清除、取消或修改 Deemix 中的手动任务。直接粘贴的 YouTube 链接仍按原有方式下载。

此来源不会自动替换或删除媒体库中的现有曲目。媒体库去重和手动替换音频仍是独立功能。
