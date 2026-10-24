---
icon: lucide/hand-heart
---

# 기여하기

기여를 환영합니다 — 버그 보고, 기능 요청, 코드, 번역 모두 도움이 됩니다. 번역은 앱, 이 문서, 또는 둘 다에 대한 것일 수 있습니다: [번역](#translating)을 참고하세요.

## 이슈와 기능 요청

[GitHub 이슈 트래커](https://github.com/henriquesebastiao/downtify/issues)를 사용하세요. 새 이슈를 열기 전에 중복을 피하도록 기존 이슈를 검색하세요.

버그 보고에는 다음을 포함하세요.

- Downtify 버전
- 설치 방법(Docker run, Docker Compose, Umbrel, …)
- 재현 단계
- 기대한 것과 실제로 일어난 일
- 관련 로그

## 개발 환경

### 사전 요구 사항

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (Python 패키지 관리자)
- ffmpeg (`PATH`에 있어야 함)

### 클론 및 설치

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 개발 모드로 실행

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

프런트엔드 개발 서버는 API 요청을 백엔드로 프록시하므로 Vite URL(보통 `http://localhost:5173`)만 열면 됩니다.

### 테스트 실행

```bash
uv run pytest
```

### 프로덕션용 프런트엔드 빌드

```bash
cd frontend && npm run build
```

컴파일된 파일은 `frontend/dist/`에 생기며 백엔드가 제공합니다.

### 문서 작업하기

문서는 `docs/`의 Markdown 파일로, [VitePress](https://vitepress.dev/)와 웹 앱과 디자인 토큰을 공유하는 사용자 지정 테마(`docs/.vitepress/`)로 정적 사이트로 빌드됩니다.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

다른 페이지는 상대 `.md` 경로로 링크하고(`[가사](lyrics.md)`), 콜아웃에는 `::: tip 제목` … `:::`을 사용하세요(`info`, `tip`, `warning`, `danger`). 새 페이지는 `docs/.vitepress/nav.mjs`의 사이드바에 추가합니다(제목은 `docs/.vitepress/locales/`의 각 언어 파일에). 죽은 링크나 존재하지 않는 제목으로의 링크가 있으면 빌드가 실패합니다.

`docs/`의 영어 페이지가 원본이며, 다른 모든 언어는 각자의 폴더(`docs/pt-BR/…`)에 이를 반영합니다. 영어 페이지를 바꿀 때 번역을 함께 갱신할 필요는 없습니다 — 번역자가 뒤따릅니다 — 하지만 `docs/`에서 `npm test`를 실행하세요. 새 페이지는 각 언어에 영어 전용 스텁이 필요하며(`npm run i18n -- stubs`), 없으면 테스트가 알려줍니다.

## 프로젝트 구조

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

## 번역

Downtify에는 번역할 것이 두 가지 있으며, 어느 쪽이든 — 또는 둘 다 — 맡을 수 있습니다.

| 번역 대상 | 위치 | 가이드 |
|---------------|-------|-------|
| **앱**(인터페이스) | `frontend/src/i18n/locales/<code>.js` | [앱 번역하기](features/internationalization.md#translating-the-app) |
| **문서**(이 페이지들) | `docs/<code>/`와 `docs/.vitepress/locales/<code>.mjs` | [문서 번역하기](features/internationalization.md#translating-the-documentation) |

둘은 독립적입니다. 한 언어가 한쪽에는 있고 다른 쪽에는 아직 없을 수 있으며, 풀 리퀘스트에는 앱 번역만, 문서만, 또는 둘 다 담을 수 있습니다. 부분적인 작업도 환영합니다 — 번역되지 않은 문자열은 앱에서 영어로 대체되고, 번역되지 않은 페이지는 문서에서 영어로 남습니다.

문서를 위한 빠른 시작(`docs/`에서):

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

자세한 내용은 [국제화](features/internationalization.md)를 참고하세요: 그대로 두어야 할 것, 완전히 새로운 언어를 추가하는 방법, 버튼 이름을 앱과 일치하도록 번역하는 방법.

## 풀 리퀘스트

- 저장소를 포크하고 `main`에서 브랜치를 만드세요
- 변경은 집중해서 — PR 하나에 기능이나 수정 하나
- 백엔드 로직을 건드리면 테스트를 추가하거나 갱신하세요
- 제출하기 전에 `uv run pytest`를 실행하세요
- PR은 `main`을 대상으로 여세요

Downtify가 도움이 되었다면 GitHub에 별을 남겨 주세요 — 프로젝트가 성장하는 데 도움이 됩니다.
