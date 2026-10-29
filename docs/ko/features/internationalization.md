---
icon: lucide/languages
---

# 국제화

Downtify는 서로 독립적인 두 곳에서 번역됩니다: **앱**(인터페이스)과 이 **문서**입니다. 둘 다 기본 언어는 **영어**이며, 기본으로 아홉 개 언어가 더 들어 있습니다.

## 언어 바꾸기

### 앱

**설정 → 언어**로 가서 선호하는 언어를 고르세요. 선택은 브라우저의 `localStorage`에 저장되고 페이지를 새로고침하지 않아도 즉시 적용됩니다. 페이지는 매번 로드될 때와 언어를 바꿀 때마다 서버에도 알려(`settings.json`의 `ui_language` 항목, [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate) 참고), 브라우저 없이 실행되는 작업도 내 언어를 알게 합니다 - 아티스트의 곡 하나가 내려받기를 마칠 때 백그라운드에서 가져오는 아티스트 소개가 그 언어로 들어옵니다([다운로드가 끝났을 때](artist-images.md#when-a-download-finishes) 참고). 직접 할 일은 없습니다. 이 기능이 생기기 전에 언어를 골랐다면 다음에 Downtify를 열 때 반영됩니다. 여러 브라우저가 서로 다른 언어로 설정되어 있으면 마지막으로 로드했거나 바꾼 쪽이 이깁니다.

### 문서

문서는 브라우저가 선호하는 언어로 번역되어 있으면 그 언어로, 아니면 영어로 열립니다. 상단 바 오른쪽의 **지구본 버튼**으로 언제든 언어를 바꿀 수 있으며 같은 페이지(와 섹션)에 머뭅니다. 선택은 브라우저에 기억되고, 그 뒤로는 다른 언어를 고를 때까지 브라우저 언어보다 우선합니다.

아직 번역되지 않은 페이지는 안내와 함께 영어 텍스트를 보여주므로, 모든 언어에 모든 페이지가 항상 있습니다.

## 사용 가능한 언어

| 코드 | 언어 | 앱 | 문서 |
| ------- | ------------------ | --- | ---- |
| `en` | English (기본값) | ✓ | ✓ |
| `es` | Español | ✓ | ✓ |
| `pt-BR` | Português (Brasil) | ✓ | ✓ |
| `fr` | Français | ✓ | ✓ |
| `tr` | Türkçe | ✓ | ✓ |
| `el` | Ελληνικά | ✓ | ✓ |
| `hu` | Magyar | ✓ | ✓ |
| `bg` | Български | ✓ | ✓ |
| `de` | Deutsch | ✓ | ✓ |
| `ko` | 한국어 | ✓ | ✓ |

개발자를 위한 레퍼런스 페이지 — [API 레퍼런스](../api-reference.md), [모바일 클라이언트 규약](../mobile-client-contract.md), 변경 내역 — 는 모든 언어에서 영어로 유지됩니다.

## 번역 기여하기

앱, 문서, 또는 둘 다 번역할 수 있습니다. 이들은 파일이 따로 있는 별개의 작업이므로, 풀 리퀘스트에는 둘 중 하나만 담을 수도 있고 — 한 언어를 먼저 한쪽에 추가하고 나중에 다른 쪽에 추가할 수도 있습니다.

| 번역 대상 | 파일 위치 | 완료 조건 |
| ------------- | ------------------- | --------- |
| **앱만** | `frontend/src/i18n/locales/<code>.js` | 언어가 **설정 → 언어**에 나타남 |
| **문서만** | `docs/.vitepress/locales/<code>.mjs`와 `docs/<code>/`의 Markdown 페이지 | 언어가 문서의 지구본 메뉴에 나타남 |
| **둘 다** | 위의 모든 것 | 둘 다 |

언어가 앱에 있어야 문서에 추가할 수 있는 것은 아니며, 그 반대도 마찬가지입니다.

## 앱 번역하기

앱에 번역을 추가하는 것은 세 단계입니다.

### 1. 영어 로케일 파일 복사

로케일 파일은 `frontend/src/i18n/locales/`에 있습니다. 각 파일은 키가 `en.js`의 구조와 일치하는 단일 객체를 내보냅니다. 파일 이름에는 [IETF 언어 태그](https://en.wikipedia.org/wiki/IETF_language_tag)를 사용하세요.

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/it.js
```

### 2. 값 번역

키, 자리 표시자 토큰(예: `{count}`, `{name}`, `{file}`), 전체적인 형태는 바꾸지 마세요 — 오른쪽의 문자열만 바뀌어야 합니다. `language.name`은 그 언어의 **자국어** 이름(`"Français"`, `"Deutsch"`, …)으로 설정하세요 — 언어 선택기에 표시되는 라벨입니다.

### 3. 로케일 등록

`frontend/src/i18n/index.js`의 `AVAILABLE_LOCALES`에 import와 항목을 추가하세요.

```js
import it from './locales/it.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  // …
  { code: 'it', name: 'Italiano', messages: it }, // new
]
```

프런트엔드를 다시 빌드하면 내 언어가 **설정 → 언어**에 자동으로 나타납니다.

```bash
cd frontend && npm run build
```

### 앱 번역 팁

- 없는 키는 영어로 대체되므로 부분 번역도 잘 동작합니다 — 가진 만큼으로 PR을 보내세요.
- 숫자에 따라 달라지는 문자열은 복수형을 가진 객체입니다. 예: `tracks: { one: '{count} track', other: '{count} tracks' }`. 형태는 해당 언어에 대한 브라우저의 [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules)로 선택되므로, 내 언어가 쓰는 형태(`zero`, `one`, `two`, `few`, `many`, `other`)를 추가하세요 — `other`는 필수입니다. 숫자는 언어에 맞게 자동으로 서식이 지정됩니다.
- `{count}`나 `{file}` 같은 자리 표시자 토큰은 그대로 두어야 합니다. 런타임에 대체됩니다.
- 문자열은 간결하게 — UI는 빽빽하게 배치되어 있어 아주 긴 번역은 어색하게 줄바꿈될 수 있습니다.
- 번역한 뒤 `frontend/`에서 `npm run dev`를 실행하고 모든 페이지를 내 언어로 둘러보며 넘치거나 맥락에서 어색한 것을 찾아보세요.

## 문서 번역하기

영어가 원본이며 `docs/`에 있습니다. 다른 모든 언어는 코드 이름의 폴더(`docs/pt-BR/`)를 가지며 영어와 **같은 파일 이름**을 쓰고, 사이트 자체 텍스트를 위한 파일 하나(`docs/.vitepress/locales/pt-BR.mjs`: 사이드바 제목, 검색창, 푸터, 콜아웃 라벨)가 있습니다. 아직 번역되지 않은 페이지는 안내를 보여주고 영어 페이지를 포함하는 작은 스텁입니다.

### 기존 언어의 페이지 번역하기

`docs/`에서:

```bash
npm install
npm run i18n -- status pt-BR           # what is translated, what is English-only, what is out of date
npm run i18n -- start pt-BR features/users.md
```

`start`는 스텁 `docs/pt-BR/features/users.md`를 영어 페이지의 사본으로 바꿉니다. 그 자리에서 번역한 다음 확인하세요.

```bash
npm test             # the translated pages must keep the English page's structure
npm run dev          # read it in the browser, in your language
```

페이지가 잘 읽히면 풀 리퀘스트를 여세요. 부분 작업도 환영합니다 — 손대지 않은 페이지는 그냥 영어로 남습니다.

### 문서에 언어 추가하기

1. `docs/.vitepress/locales/en.mjs`를 `docs/.vitepress/locales/<code>.mjs`로 복사해 번역합니다: 자국어 `name`, 사이트 텍스트(`ui`), 콜아웃 라벨(`containers`), 사이드바 제목(`nav`).
2. `docs/.vitepress/locales/index.mjs`에 등록합니다.
3. 영어 전용 스텁으로 페이지를 만듭니다: `npm run i18n -- stubs <code>`.
4. `npm run i18n -- start <code> <page>`로 페이지를 하나씩 번역합니다.

언어는 등록되는 즉시 지구본 메뉴와 브라우저 언어 감지에 나타납니다.

### 유지할 것과 번역할 것

- 텍스트, 제목, 표 셀, 콜아웃 제목, 홈 페이지 front matter의 `title`/`text` 값은 **번역**합니다.
- 코드 블록, 인라인 `code`, URL, 환경 변수, API 경로와 필드 이름, 파일과 폴더 이름, front matter 키와 `icon:`, `link:` 값은 **그대로 둡니다**. 코드 블록 안의 주석을 번역해도 됩니다.
- **링크**: 영어 페이지의 상대 `.md` 링크(`[가사](lyrics.md#sidecar-lrc-file)`)를 그대로 유지하세요. 영어로만 있는 페이지로의 링크도 여전히 동작합니다. 홈 페이지에서는 링크를 언어 접두사와 함께 씁니다(`/pt-BR/features/player/`).
- **제목**: 같은 제목을 같은 순서, 같은 수준으로 유지하세요. 섹션 링크(`#sidecar-lrc-file`)는 번역된 페이지가 영어 제목 id를 재사용하므로 모든 언어에서 계속 동작합니다 — id를 직접 쓰거나 번역하지 않습니다.
- **버튼과 설정 이름**: 앱에는 모든 라벨의 자체 번역이 있습니다. 페이지가 독자가 화면에서 보는 것과 일치하도록 굵게 표시해 그것을 사용하세요: `frontend/src/i18n/locales/<code>.js`에서 라벨을 찾아보세요. 앱이 그 언어로 아직 번역되지 않았다면 영어 라벨을 유지하세요.
- **콜아웃** (`::: tip 제목`): 종류(`info`, `tip`, `warning`, `danger`)는 유지하고 제목을 번역하세요. 제목이 없는 콜아웃에는 로케일 파일의 `containers`에 있는 단어가 라벨로 붙습니다.
- **어조**: 그 언어의 독자를 위해 쓰세요 — 페이지는 가이드이며 단어 단위의 직역이 아닙니다.

### 번역을 최신 상태로 유지하기

영어 페이지가 바뀌어도 그 번역이 같은 풀 리퀘스트에서 바뀔 필요는 없습니다. 번역된 페이지는 계속 동작하며, `npm run i18n -- status <code>`는 번역된 뒤 영어 원본이 바뀐 페이지를 나열합니다. 그것들을 갱신하는 것은 좋은 첫 기여입니다.

테스트(`docs/`의 `npm test`)는 모든 언어에 모든 페이지와 모든 사이트 텍스트가 있는지, 그리고 번역된 페이지가 영어 페이지의 제목, 코드 블록, 표, 콜아웃, 링크를 여전히 갖고 있는지 확인합니다.
