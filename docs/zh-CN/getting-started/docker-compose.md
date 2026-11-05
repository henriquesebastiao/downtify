---
icon: lucide/file-code
---

# Docker Compose

对于需要长期运行的家庭服务器，推荐使用 Docker Compose 部署 Downtify。这样更便于更新、备份和调整配置。

## 最简配置

创建 `docker-compose.yml` 文件：

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped

volumes:
  downtify_data:
```

启动服务：

```bash
docker compose up -d
```

打开 **[http://localhost:8000](http://localhost:8000)**。

## 与 slskd（Soulseek）搭配使用

如需将 [slskd 用作音频来源](../features/slskd-navidrome.md)，也要把 slskd 的下载目录挂载到 Downtify 中，并确保使用的是 slskd 容器实际写入的**同一个主机目录**：

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

然后在 **Settings → Audio sources → slskd** 中启用 slskd，填写其 URL（两个容器位于同一 Docker 网络时，例如 `http://slskd:5030`）和 API 密钥，并将下载目录设为 `/slskd`。

## 添加现有音乐文件夹

如需让媒体库读取主机上已有的音乐收藏，请按相同方式[挂载目录](../features/external-library.md)，再在 **Settings → Library** 中填写容器内的路径：

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## 让应用发现服务器

[移动应用](../features/mobile-apps.md#finding-the-server-on-your-network)通过 mDNS 列出网络中的 Downtify 服务器。在 Docker 默认的 bridge 网络中，广播不会离开 Docker，因此手机无法发现服务器。若要让服务器出现在列表中，请将容器设为使用主机网络。此时 `ports:` 映射不再生效，Downtify 会直接监听 `DOWNTIFY_PORT`：

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    network_mode: host
    environment:
      - DOWNTIFY_PORT=8000
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

也可以直接在应用中输入服务器地址（`http://<主机 IP>:8000`）；除自动发现外，其他功能不受影响。

## 自定义端口

如果主机上的 8000 端口已被占用，可以映射其他主机端口，并设置 `DOWNTIFY_PORT`，让容器在内部监听对应端口：

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '9090:30321'
    environment:
      - DOWNTIFY_PORT=30321
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

也可以在 **Settings → Server → Port** 中选择端口，而不设置 `DOWNTIFY_PORT`（如果设置了环境变量，则以它为准）。使用默认 bridge 网络时，需将 `ports:` 映射改为相同端口并重新创建容器。详见[更改端口](../features/server.md#changing-the-port)。

## 使用自定义 DNS（推荐）

部分互联网服务提供商和企业网络会屏蔽 YouTube。指定 DNS 解析器有助于提高连接稳定性：

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    dns:
      - 1.1.1.1
      - 1.0.0.1
    restart: unless-stopped
```

## 更新

```bash
docker compose pull
docker compose up -d
```

音乐和设置会保留在卷中。

## 卷

| Compose 文件中的路径 | 用途 |
|------------------------------|---------|
| `./downloads:/downloads` | 已下载的音频文件（本地目录） |
| `downtify_data:/data` | 应用数据库和设置（命名卷） |

如果希望自行管理数据目录，也可以将命名卷替换为本地路径（`./data:/data`）。
