---
icon: lucide/cookie
---

# YouTube Cookies

Downtify 从 YouTube 获取音频。大多数情况下可以匿名访问，但也有例外：

- **显式内容/年龄限制曲目。** YouTube 只向已登录的成年账户提供这些内容。没有 cookies 时，下载会失败。
- **机器人验证。** 在数据中心 IP（VPS、部分 VPN）上，YouTube 有时会返回“Sign in to confirm you're not a bot”，而不是提供音频。

提供 `cookies.txt` 可同时解决这两类问题：yt-dlp 会像已登录的浏览器会话一样访问 YouTube。

## 上传 cookies.txt（推荐）

1. 安装 cookie 导出扩展：[Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)（Chrome/Edge）或 [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)（Firefox）。
2. 登录 Google 账户后打开 `youtube.com`，导出该站点的 cookies；文件必须采用 **Netscape** 格式。
3. 在 Downtify 中打开 **Settings**（⚙️）→ **YouTube cookies** → **Upload cookies.txt**。

上传时会验证文件；如果文件不是 Netscape cookie jar 格式，系统会立即拒绝，而不会让后续下载悄然全部失败。如果文件中不含 `youtube.com` 或 `google.com` cookies，系统会发出警告，因为这通常意味着导出时选错了标签页。

上传后，可在同一页面**替换**（上传另一个文件）或**删除**该文件。

::: tip 适用于各种平台的方式
通过 Web 界面上传无需绑定挂载、文件路径或命令行操作，因此也适用于 Docker Desktop for Windows；在该环境中，将 `cookies.txt` 挂载进容器往往很麻烦。
:::

## 存储位置

上传的文件会保存为 Downtify 数据目录（默认 `/data`）中的 `cookies.txt`，与 `settings.json` 和 Playlist Monitor 数据库位于同一卷。因此，**容器更新后仍会保留**：拉取新镜像并重新创建容器时，只要 `/data` 仍使用命名卷或绑定挂载，cookies 就会保留。

## 改用环境变量

原有的 [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube) 变量仍然可用，且**优先级更高**：

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

设置此变量后，设置页面会将 cookies 区域显示为锁定状态，并拒绝上传和删除操作，因为此配置由部署环境负责管理，Downtify 不得覆盖它不管理的文件。若要改用 Web 界面管理 cookies，请取消设置该变量并重新创建容器。

`DOWNTIFY_COOKIES_FROM_BROWSER` 可直接从浏览器配置文件读取 cookies，但这要求容器内部能够访问浏览器的 cookie 存储，因此在 Docker 中通常不适用。

## 保持 cookies 有效

- Cookies 会过期。如果年龄限制内容的下载再次失败，请导出新文件并上传替换。
- 从之后会关闭的**私人/无痕窗口**导出，通常可以获得更长效的会话，因为关闭普通窗口可能会使导出的会话失效。
- 某些地区要求 Google 账户完成完整身份验证，YouTube 才会提供年龄限制内容。仅登录账户并不总是足够。

::: warning 请像保护密码一样保护此文件
`cookies.txt` 包含 Google 账户的有效会话令牌。任何能读取该文件的人都可以在 YouTube 上冒充你。在文件系统支持的情况下，Downtify 会使用仅所有者可读的权限保存文件，并且绝不会通过 API 暴露其内容，只会提供是否已配置、文件大小和修改时间等信息。如果不想让主账户承担风险，可使用专门的 Google 账户。
:::
