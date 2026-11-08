---
icon: lucide/smartphone
---

# 安装为应用（PWA）

Downtify Web 界面是渐进式 Web 应用（PWA）。在 iOS 和 Android 上，你可以将它添加到主屏幕；启动后会像原生应用一样以全屏模式运行，不显示浏览器地址栏和导航控件。

## iOS（Safari）

1. 在 Safari 中打开 Downtify。
2. 点击 **Share** 按钮。
3. 点击 **Add to Home Screen**。

Downtify 图标会出现在主屏幕上，点击后将在独立窗口中启动。

## Android（Chrome）

1. 在 Chrome 中打开 Downtify。
2. 点击 **⋮** 菜单。
3. 点击 **Add to Home screen**（如果 Chrome 直接提供该选项，也可点击 **Install app**）。

## 工作原理

`frontend/index.html` 引用了[渐进式 Web 应用清单](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest)（`/manifest.json`），其中设置了 `"display": "standalone"` 和 `start_url: "/"`，还包含 Android 主屏幕快捷方式和应用切换器使用的图标。Chrome/Android 会读取这些信息，以带有独立图标的全屏模式安装应用。

iOS Safari 在“添加到主屏幕”时不会读取清单中的 `display` 或图标字段，因此 `index.html` 还需设置独立的 `apple-mobile-web-app-capable` 和 `apple-touch-icon` `<meta>` / `<link>` 标签。这些标签与清单同时配置，使两个平台都能以带 Downtify 图标的全屏独立模式运行。

此应用不支持离线使用，也没有 service worker。Downtify 界面只有在能够连接已配对的后端时才有用，因此它是“可安装的全屏 Web 应用”，而不是可离线使用的应用。
