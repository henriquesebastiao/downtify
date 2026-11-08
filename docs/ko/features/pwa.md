---
icon: lucide/smartphone
---

# 앱으로 설치(PWA)

Downtify의 웹 UI는 Progressive Web App입니다. iOS와 Android 모두에서 홈 화면에 추가할 수 있으며, 주소 표시줄이나 브라우저 탐색 UI 없이 네이티브 앱처럼 전체 화면으로 실행됩니다.

## iOS (Safari)

1. Safari에서 Downtify를 엽니다
2. **공유** 버튼을 탭합니다
3. **홈 화면에 추가**를 탭합니다

Downtify 아이콘이 홈 화면에 나타나고 독립된 창으로 실행됩니다.

## Android (Chrome)

1. Chrome에서 Downtify를 엽니다
2. **⋮** 메뉴를 탭합니다
3. **홈 화면에 추가**를 탭합니다(Chrome이 바로 제안하면 **앱 설치**)

## 작동 방식

`frontend/index.html`은 `"display": "standalone"`과 `start_url: "/"`를 지정하는 [웹 앱 매니페스트](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest)(`/manifest.json`)를 연결하며, Android가 홈 화면 바로가기와 앱 전환기에 쓰는 아이콘도 함께 지정합니다. Chrome/Android는 이를 읽어 앱을 전체 화면과 고유 아이콘으로 설치합니다.

iOS Safari는 "홈 화면에 추가"를 할 때 매니페스트의 `display`나 아이콘 필드를 전혀 읽지 않습니다. `index.html`에 자체 `apple-mobile-web-app-capable`, `apple-touch-icon` `<meta>`/`<link>` 태그가 필요하며, 이 태그를 매니페스트와 함께 설정해 두 플랫폼 모두 Downtify 아이콘과 함께 같은 독립 전체 화면 동작을 얻도록 했습니다.

오프라인 지원이나 서비스 워커는 없습니다. Downtify의 UI는 연결된 백엔드에 닿을 수 있을 때만 쓸모가 있으므로, 이것은 "설치 가능한 전체 화면 웹 앱"이지 오프라인에서 동작하는 앱이 아닙니다.
