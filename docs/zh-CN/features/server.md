---
icon: lucide/hard-drive
---

# 服务器设置

**Settings → Server** 用于配置服务器本身的运行方式。只有管理员可以查看此页面（参见[用户与登录](users.md#admins-and-users)）。

## 更改端口

Downtify 默认监听 **8000** 端口。管理员可在 **Settings → Server → Port** 中选择其他端口（1024–65535）：

- **Save**：保存端口，在服务器下次启动时生效。
- **Save and restart**：立即重启服务器并使用新端口。正在进行的下载会停止，页面和应用会重新连接。如果你是通过服务器自身地址打开页面（例如 `http://nas:8000`），页面会等待服务器重启并自动打开新地址；登录状态会保留。

如果端口由 `DOWNTIFY_PORT`（或 `PORT`）环境变量，或命令行中的 `--port` 指定，则这些配置始终优先。设置页会显示当前端口，但不能编辑，并会说明由哪个配置项控制。移除该配置项并重启后，才能在 Settings 中选择端口。

::: warning Docker bridge 网络会映射固定端口
使用默认 Docker 配置（`ports: - '8000:8000'`）时，容器端口必须与映射一致。在 Settings 中更改端口后，也要将映射改为新端口（`'9000:9000'`）并重新创建容器，或改用 `network_mode: host`，否则无法访问 Downtify。如需重新连接，可将 `DOWNTIFY_PORT` 设为旧端口；它的优先级高于 Settings。
:::

如果使用[反向代理](mobile-apps.md#behind-a-reverse-proxy)，也要将代理指向新端口。[已配对的应用](mobile-apps.md)会继续使用原有地址；更改端口后，请在应用中输入新端口。
