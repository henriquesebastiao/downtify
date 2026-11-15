---
icon: lucide/languages
---

# 国际化

Downtify 的翻译分为两个相互独立的部分：**应用**（界面）和本文档。两者的默认语言均为**英语**。应用和文档分别维护可用语言列表；两者目前都支持简体中文。

## 切换语言

### 应用

前往 **Settings → Language**，选择所需语言。选项保存在浏览器的 `localStorage` 中，无需重新加载页面即可立即生效。每次加载页面或更改语言时，页面也会将所选语言告知服务器（`settings.json` 中的 `ui_language` 条目，参见 [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate)），以便无浏览器参与的后台任务也能使用对应语言。例如，某首曲目下载完成后后台获取的艺人简介会使用该语言（参见[下载完成时](artist-images.md#when-a-download-finishes)）。无需额外操作：如果你在此功能推出前就选好了语言，下次打开 Downtify 时会自动读取。多个浏览器设置了不同语言时，以最近加载页面或更改语言的浏览器为准。

### 文档

如果文档已翻译为浏览器首选语言，文档站点会以该语言打开；否则使用英语。你可以随时点击顶栏右侧的**地球图标**切换语言，切换后仍停留在同一页面和章节。浏览器会记住你的选择；此后该设置优先于浏览器语言，直到你再次选择其他语言。

尚未翻译的页面会显示提示和英文原文，因此每种语言始终都能访问全部页面。

## 可用语言

| Code    | Language           | App | Docs |
| ------- | ------------------ | --- | ---- |
| `en`    | English (default)  | ✓   | ✓    |
| `es`    | Español            | ✓   | ✓    |
| `pt-BR` | Português (Brasil) | ✓   | ✓    |
| `fr`    | Français           | ✓   | ✓    |
| `tr`    | Türkçe             | ✓   | ✓    |
| `el`    | Ελληνικά           | ✓   | ✓    |
| `hu`    | Magyar             | ✓   | ✓    |
| `bg`    | Български          | ✓   | ✓    |
| `de`    | Deutsch            | ✓   | ✓    |
| `ko`    | 한국어             | ✓   | ✓    |
| `zh-CN` | 简体中文           | ✓   | ✓    |
| `zh-TW` | 繁體中文           | ✓   | —    |

面向开发者的参考页面——[API 参考](../api-reference.md)和更新日志——目前在所有语言版本中均保留英文。提供相应语言译文的站点也可以翻译[移动客户端协议](../mobile-client-contract.md)。

## 参与翻译

你可以翻译应用、文档，或两者兼顾。它们是独立的工作，文件也各自分开，因此一个 Pull Request 可以只包含其中一部分；也可以先为其中一方添加语言，再于之后添加另一方。

| 翻译内容 | 文件位置 | 完成标志 |
| ------------- | ------------------- | --------- |
| **The app only** | `frontend/src/i18n/locales/<code>.js` | the language appears in **Settings → Language** |
| **The documentation only** | `docs/.vitepress/locales/<code>.mjs` and the Markdown pages in `docs/<code>/` | the language appears in the docs' globe menu |
| **Both** | all of the above | both |

文档可以添加尚未在应用中支持的语言，反之亦然。

## 翻译应用

为应用添加翻译分为三个步骤：

### 1. 复制英语语言文件

语言文件位于 `frontend/src/i18n/locales/`。每个文件导出一个对象，其键结构与 `en.js` 一致。文件名使用 [IETF 语言标签](https://en.wikipedia.org/wiki/IETF_language_tag)。

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/it.js
```

### 2. 翻译文本值

保留键、占位符（例如 `{count}`、`{name}`、`{file}`）和整体结构不变，只翻译右侧的字符串。将 `language.name` 设为该语言的**本地名称**（如 `"Français"`、`"Deutsch"`），它会显示在语言选择器中。

### 3. 注册语言

在 `frontend/src/i18n/index.js` 中添加导入语句，并在 `AVAILABLE_LOCALES` 中添加对应项：

```js
import it from './locales/it.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  // …
  { code: 'it', name: 'Italiano', messages: it }, // new
]
```

重新构建前端后，该语言就会自动显示在 **Settings → Language** 中：

```bash
cd frontend && npm run build
```

### 应用翻译提示

- 缺少的键会回退到英语，因此可以逐步完成翻译；完成一部分后也欢迎提交 PR。
- 与数量相关的字符串使用包含复数形式的对象，例如 `tracks: { one: '{count} track', other: '{count} tracks' }`。系统会根据浏览器的 [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) 选择对应形式，因此请按语言规则提供所需形式（`zero`、`one`、`two`、`few`、`many`、`other`）；其中 `other` 为必需项。数字会根据语言自动格式化。
- `{count}`、`{file}` 等占位符必须保持不变；运行时会替换为实际内容。
- 文本应简洁；界面布局较紧凑，过长的翻译可能会产生不自然的换行。
- 翻译完成后，在 `frontend/` 中运行 `npm run dev`，以所选语言浏览每个页面，检查文字溢出或上下文表达不自然的问题。

## 翻译文档

英语原文位于 `docs/`。其他语言都使用以语言代码命名的目录（例如 `docs/pt-BR/`），其中的文件名与英语原文**完全相同**；此外，还需为站点界面文本提供一个文件（例如 `docs/.vitepress/locales/pt-BR.mjs`），用于侧边栏标题、搜索框、页脚及提示框标签等。尚未翻译的页面会使用简短占位文件显示说明并引入英文原文。

### 翻译现有语言的页面

From `docs/`:

```bash
npm install
npm run i18n -- status pt-BR           # what is translated, what is English-only, what is out of date
npm run i18n -- start pt-BR features/users.md
```

`start` 会将占位文件 `docs/pt-BR/features/users.md` 替换为对应英文页面的副本。直接在该文件中翻译，然后进行检查：

```bash
npm test             # 翻译页面必须保留英文页面的结构
npm run dev          # 在浏览器中以目标语言查看页面
```

页面表达自然后即可提交 Pull Request；也欢迎提交部分翻译，尚未处理的页面会继续显示英文。

### 为文档添加语言

1. 将 `docs/.vitepress/locales/en.mjs` 复制为 `docs/.vitepress/locales/<code>.mjs` 并翻译其中内容：语言的本地名称 `name`、站点文字 `ui`、提示框标签 `containers` 和侧边栏标题 `nav`。
2. 在 `docs/.vitepress/locales/index.mjs` 中注册该语言。
3. 创建英文回退占位页：`npm run i18n -- stubs <code>`。
4. 使用 `npm run i18n -- start <code> <page>` 逐页翻译。

注册后，该语言会出现在地球图标菜单和浏览器语言检测结果中。

### 应保留和翻译的内容

- **需要翻译**：正文、标题、表格单元格、提示框标题，以及首页 Front Matter 中的 `title`/`text` 值。
- **保持原样**：代码块、行内 `code`、URL、环境变量、API 路径和字段名、文件及目录名，以及 Front Matter 的键、`icon:` 和 `link:` 值。代码块中的注释可以翻译。
- **链接**：英文原文中的相对 `.md` 链接（例如 `[Lyrics](lyrics.md#sidecar-lrc-file)`）须原样保留。指向仅有英文的页面仍然有效。首页链接使用语言前缀（例如 `/pt-BR/features/player/`）。
- **标题**：保留相同的标题、顺序和层级。章节链接（如 `#sidecar-lrc-file`）在各语言中仍然有效，因为翻译页会沿用英文标题 ID；不要自行编写或翻译 ID。
- **按钮和设置名称**：应用自身已翻译所有标签。为使文档与界面一致，请从 `frontend/src/i18n/locales/<code>.js` 查找并使用对应翻译，并加粗显示。如果应用尚未翻译成该语言，则保留英文标签。
- **提示框**（`::: tip Title`）：保留类型（`info`、`tip`、`warning`、`danger`），翻译标题。未设置标题的提示框会使用语言文件 `containers` 中对应类型的名称。
- **语气**：面向目标语言读者撰写；文档是操作指南，不必逐字直译。

### 保持翻译内容更新

英文页面更新时，不必在同一个 Pull Request 中同步更新译文：现有译文仍可正常使用，而 `npm run i18n -- status <code>` 会列出译文完成后英文原文又有更改的页面。更新这些页面也是很好的入门贡献。

测试（在 `docs/` 中运行 `npm test`）会检查每种语言是否都包含全部页面和站点文字，并确认译文保留了英文页面的标题、代码块、表格、提示框和链接。
