---
icon: lucide/download
---

# 安装

运行 Downtify 最快的方法是执行一条 `docker run` 命令。主机无需安装 Python、Node.js 或其他系统依赖，所需组件都已打包在镜像中。

## 前提条件

- 已安装并运行 [Docker](https://docs.docker.com/get-docker/)

## 使用 Docker 运行

```bash
docker run -d \
  --name downtify \
  -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

将 `/path/to/music` 替换为你希望保存音乐的目录。

容器启动后，在浏览器中打开 **[http://localhost:8000](http://localhost:8000)**。

## 卷

| 卷 | 用途 |
|--------|---------|
| `/downloads` | 下载的音频文件 |
| `/data` | 应用数据库和持久化设置 |

这两个卷中的数据会在容器重启和升级后保留。`/downloads` 可以映射到主机上的任意目录，也可以使用 Docker 命名卷。

## 自定义端口

如需通过其他主机端口访问 Downtify，请修改 `-p` 参数左侧的端口：

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # host:container
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

然后打开 **[http://localhost:9090](http://localhost:9090)**。

## 更新

拉取最新镜像并重新创建容器：

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

音乐和设置会保留在卷中。

## 接下来

- **[Docker Compose](docker-compose.md)**：更便于长期管理容器
- **[环境变量](environment-variables.md)**：配置反机器人验证及其他高级选项
- **[下载设置](../features/download-settings.md)**：选择音频格式和比特率
