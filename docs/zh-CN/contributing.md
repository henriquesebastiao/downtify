---
icon: lucide/hand-heart
---

# 参与贡献

欢迎参与贡献：错误报告、功能建议、代码和翻译都能帮助项目改进。你可以翻译应用、本文档，或两者兼顾；详见[翻译](#translating)。

## 问题与功能建议

请使用 [GitHub 问题跟踪器](https://github.com/henriquesebastiao/downtify/issues)。提交新问题前，请先搜索已有问题，避免重复。

报告错误时，请提供：

- Downtify 版本
- 安装方式（Docker run、Docker Compose、Umbrel 等）
- 重现步骤
- 预期结果与实际结果
- 相关日志

## 开发环境设置

### 前置条件

- Python 3.11–3.14（项目声明的支持范围为 `>=3.11,<3.15`）
- Node.js 20+
- [uv](https://github.com/astral-sh/uv)（Python 包管理器）
- ffmpeg（必须位于 `PATH` 中）

### 克隆并安装

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 以开发模式运行

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

前端开发服务器会将 API 请求代理到后端，因此只需打开 Vite URL（通常为 `http://localhost:5173`）。

### 运行测试

```bash
uv run pytest
```

### 构建生产版前端

```bash
cd frontend && npm run build
```

编译后的资源位于 `frontend/dist/`，由后端提供。

### 处理文档

文档是 `docs/` 中的 Markdown 文件，通过 [VitePress](https://vitepress.dev/) 构建为静态站点。自定义主题位于 `docs/.vitepress/`，并与 Web 应用共享设计令牌。

```bash
make doc         # 启动热重载开发服务器
make doc-build   # 构建生产站点到 docs/.vitepress/dist
```

通过相对 `.md` 路径链接其他页面（例如 `[Lyrics](lyrics.md)`），使用 `::: tip Title` … `:::` 编写提示框（类型可为 `info`、`tip`、`warning`、`danger`）。新页面需要加入 `docs/.vitepress/nav.mjs` 侧边栏，并在各语言的文件中提供标题（位于 `docs/.vitepress/locales/`）。构建会检查死链和不存在的标题锚点。

`docs/` 中的英语页面是原文；其他语言在各自目录中镜像相同的文件路径（例如 `docs/pt-BR/…`）。修改英语原文时不必同时更新译文，译者会随后跟进；但请在 `docs/` 中运行 `npm test`。新增页面时，需要为每种语言添加英文回退占位页（`npm run i18n -- stubs`）；测试会检查是否有遗漏。

## 项目结构

```
downtify/
├── downtify/          # Python backend
│   ├── api.py         # FastAPI router
│   ├── downloader.py  # yt-dlp + mutagen pipeline
│   ├── spotify.py     # Spotify embed scraping
│   ├── providers.py   # YouTube Music search
│   ├── monitor.py     # Playlist monitor
│   ├── lyrics.py      # lrclib integration
│   └── m3u.py         # M3U generation
├── frontend/          # Vue 3 + Vite frontend
│   └── src/
│       └── i18n/      # Translation files
├── docs/              # This documentation (Markdown + VitePress site)
│   ├── <page>.md      # English, the source
│   ├── pt-BR/ …       # One folder per translated language, same file names
│   └── .vitepress/
│       └── locales/   # Each language's site text and sidebar titles
├── main.py            # Entry point
├── Dockerfile
└── docker-compose.yml
```

## 翻译

Downtify 有两部分可供翻译，你可以任选其一，也可以都参与：

| 翻译内容 | 位置 | 指南 |
|---------------|-------|-------|
| **应用**（界面） | `frontend/src/i18n/locales/<code>.js` | [翻译应用](features/internationalization.md#translating-the-app) |
| **文档**（这些页面） | `docs/<code>/` 和 `docs/.vitepress/locales/<code>.mjs` | [翻译文档](features/internationalization.md#translating-the-documentation) |

两者相互独立：一种语言可以先加入其中一部分，稍后再加入另一部分；Pull Request 可以只包含应用翻译、只包含文档翻译，或同时包含两者。欢迎提交部分翻译：应用中未翻译的文本会回退到英语，文档中未翻译的页面也会继续显示英语。

从 `docs/` 开始翻译文档的快速步骤：

```bash
npm run i18n -- status pt-BR                    # 查看语言覆盖率
npm run i18n -- start pt-BR features/users.md   # 复制英文页面以供翻译
npm test                                        # 检查翻译页面的结构
```

详细说明请参见[国际化](features/internationalization.md)，其中介绍了哪些内容应保留原样、如何添加新语言，以及如何翻译按钮名称使其与应用界面一致。

## Pull Request

- Fork 仓库，并从 `main` 创建分支。
- 保持更改聚焦于单一功能或修复。
- 修改后端逻辑时添加或更新测试。
- 提交前运行 `uv run pytest`。
- 向 `main` 分支提交 Pull Request。

如果 Downtify 对你有帮助，欢迎在 GitHub 上点星支持项目。
