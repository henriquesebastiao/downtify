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
      - ./cookies.txt:/cookies.txt
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

请以可写方式挂载（不加 `:ro`），这样保活才能把轮换后的 Cookie 存回文件；只读文件仍会被使用，但会像以前一样过期。

设置此变量后，设置页面会将 cookies 区域显示为锁定状态，并拒绝上传和删除操作，因为此配置由部署环境负责管理，Downtify 不得覆盖它不管理的文件。若要改用 Web 界面管理 cookies，请取消设置该变量并重新创建容器。

`DOWNTIFY_COOKIES_FROM_BROWSER` 可直接从浏览器配置文件读取 cookies，但这要求容器内部能够访问浏览器的 cookie 存储，因此在 Docker 中通常不适用。

## 保持 cookies 有效

导出的 Cookie 并不会在固定日期过期。Google 会话是一组不断变化的 Cookie：导出它们的浏览器标签页每隔几分钟就会轮换 `__Secure-1PSIDTS`、`SIDCC` 等，而一份从未获得新值的副本最终会被拒绝。此时 yt-dlp 会记录 "The provided YouTube account cookies are no longer valid"。在 VPN 或数据中心 IP 上 YouTube 更严格，几个小时内就可能发生。

Downtify 会自动让上传的文件保持登录：

- **每次下载都会保存新值。** yt-dlp 每次下载都拿到文件的私有副本；下载结束后，YouTube 在此期间更改的 Cookie 会合并回保存的 `cookies.txt`，并且不会覆盖其他下载在此期间保存的更新值。
- **保活任务定期刷新。** 每 15 分钟（`DOWNTIFY_COOKIES_REFRESH_MINUTES`，`0` 表示关闭）Downtify 会像浏览器一样请求 Google 轮换会话 Cookie，用它们打开 `youtube.com`，并保存发生变化的部分。即使服务器连续几天什么都不下载，会话也能保持有效。
- **设置页面显示结果。** **设置 → YouTube Cookies** 会显示*已登录*、*已退出登录*、*无账号*（文件里没有 Google 会话，只有访客 Cookie）或*检查失败*，以及上次检查时间和 YouTube 上次要求机器人验证的时间。*立即检查*会马上运行保活。新上传的文件会在保存几秒后被检查。

仍需要你做的：

- **在无痕窗口中导出并关闭窗口。** 在无痕窗口中登录 YouTube，在同一标签页打开 `youtube.com/robots.txt`，导出 Cookie，然后关闭窗口。继续使用的标签页会自行轮换会话，Downtify 手里的副本几分钟内就会退出登录。如果可以，不要同时在普通窗口里使用同一个账号。
- **页面显示*已退出登录*时上传新文件。** Google 仍可能结束会话（修改密码、"退出所有设备"、安全审查）。日志也会提示：`YouTube cookies are signed out`。
- 部分地区要求 Google 账号先完成完整的身份验证，YouTube 才会提供任何年龄限制内容。仅仅登录并不总是足够。

::: info 为什么没有"使用 Google 登录"按钮
Downtify 无法替你登录 Google。Google 会拦截脚本和无头浏览器的登录（"此浏览器或应用可能不安全"），要求两步验证和设备确认，而 YouTube 已不再接受 yt-dlp 等第三方客户端的 OAuth。在 Downtify 中放一个登录表单，也意味着要把你的 Google 密码交给它。能够自动化的部分，是让导出的会话保持有效。
:::

::: tip 没有账号时的机器人验证
"Sign in to confirm you're not a bot" 取决于 IP 地址，而不是缺少 Cookie。如果在 VPN 上反复出现，更换 VPN 服务器或出口国家通常比换新 Cookie 更有效。用于大量下载的 Cookie 也会增加 YouTube 限制该账号的可能，因此使用一次性账号更稳妥。
:::

::: warning 请像保护密码一样保护此文件
`cookies.txt` 包含 Google 账户的有效会话令牌。任何能读取该文件的人都可以在 YouTube 上冒充你。在文件系统支持的情况下，Downtify 会使用仅所有者可读的权限保存文件，并且绝不会通过 API 暴露其内容，只会提供是否已配置、文件大小和修改时间等信息。如果不想让主账户承担风险，可使用专门的 Google 账户。
:::
