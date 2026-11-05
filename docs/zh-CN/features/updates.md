---
icon: lucide/download
---

# 更新通知

Downtify 每小时检查一次自己的 [GitHub Releases 页面](https://github.com/henriquesebastiao/downtify/releases)。发现新版本后，每个页面的侧边栏底部都会显示通知；在手机上，**More** 标签页会显示提示点，底部面板顶部也会显示一行通知。此外，**Settings → About** 中也会显示：

> ✦ Update 3.0.1 available

点击通知即可在 GitHub 上打开对应版本的发布页面。

## 工作原理

- 后端的后台任务（`downtify/update_check.py`）在启动时立即从 GitHub API 获取一次最新版本，之后每小时检查一次。该任务不阻塞其他操作，界面无需等待它完成。
- Web 界面每小时通过 `GET /api/check_update`（参见 [API 参考](../api-reference.md)）读取缓存结果；发现新版本时显示通知。
- 版本号按数字比较（`2.10.0` 并不小于 `2.9.0`，与普通字符串比较不同）；发布标签开头的可选 `v` 前缀会被忽略。

## 无法连接 GitHub 时

检查失败（例如主机离线或触发 GitHub 速率限制）时，系统会记录日志，并在下一次每小时检查时重试。在重试前，已有结果（如果存在）会继续生效。检查失败不会阻止 Downtify 的任何其他功能，也不会向用户显示错误。

## 不会自动下载更新

此功能只会**通知**你有新版本可用，Downtify 不会自行更新。要实际更新，请拉取新镜像并重新创建容器：

```bash
docker compose pull
docker compose up -d
```
