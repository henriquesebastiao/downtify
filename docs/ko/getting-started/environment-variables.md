---
icon: lucide/settings
---

# 환경 변수

모든 환경 변수는 선택 사항입니다. Downtify는 아무것도 설정하지 않아도 바로 동작합니다.

## 핵심

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `DOWNTIFY_PORT` | _(설정 안 됨)_ | 서버가 (컨테이너 안에서) 수신하는 포트. 설정하지 않으면 **설정 → 서버 → 포트**에서 고른 포트, 그것도 없으면 `8000`입니다. 설정하면 이 값이 우선하며 설정의 해당 필드는 잠깁니다. 다른 호스트 포트를 노출하려면 포트 매핑의 왼쪽을 바꾸세요. [포트 변경](../features/server.md#changing-the-port)을 참고하세요. |
| `DOWNLOAD_DIR` | `/downloads` | 오디오 파일을 저장하는 디렉터리. 라이브러리를 다른 경로에 마운트한다면 바꾸세요. |
| `HOST` | `0.0.0.0` | 웹 서버의 바인드 주소. |
| `DOWNTIFY_LOG_LEVEL` | `info` | 애플리케이션 로그 수준(`debug`, `info`, `warning`, …). |
| `TZ` | `UTC` | 로컬 시간대(IANA 이름, 예: `America/Sao_Paulo`). 아래 `DOWNTIFY_MONITOR_SYNC_TIME`을 해석하는 데 쓰입니다. |

## 재생목록 모니터

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `DOWNTIFY_MONITOR_SYNC_TIME` | _(설정 안 됨)_ | 간격이 하루 이상(매일, 매주, 2주, 매월)인 [재생목록 모니터](../features/playlist-monitor.md#choosing-a-daily-sync-time) 동기화가 실행될 시각(24시간 `HH:MM`, 위 `TZ` 기준 현지 시각). 설정하지 않으면 이전 점검으로부터 정확히 한 간격 뒤에, 어떤 시각이든 그대로 동기화합니다. |

```yaml
environment:
  - TZ=America/Sao_Paulo
  - DOWNTIFY_MONITOR_SYNC_TIME=03:00
```

## 모바일 앱과 로그인

[모바일 앱](../features/mobile-apps.md)과 [사용자와 로그인](../features/users.md)을 참고하세요. `DOWNTIFY_DISABLE_AUTH`가 `true`가 아니면 로그인이 필요합니다. 이전 버전의 `DOWNTIFY_REQUIRE_SIGN_IN`은 더 이상 쓰이지 않습니다(설정되어 있는 동안 경고가 로그에 남습니다).

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `DOWNTIFY_DISABLE_AUTH` | `false` | `true`로 하면 계정이 꺼집니다. 아무도 로그인하지 않으며, 서버에 접속한 사람은 누구나 관리자로 사용합니다. 로그인 페이지, 로그아웃 버튼, **설정 → 사용자 관리**, **설정 → 일반**의 계정 부분이 사라집니다. 페어링된 앱은 계속 동작합니다. `false`로 되돌리거나 제거하면 로그인이 다시 필요해지며 계정은 그대로입니다. [사용자와 로그인](../features/users.md#turning-accounts-off)을 참고하세요. |
| `DOWNTIFY_TRUSTED_PROXIES` | _(설정 안 됨)_ | 리버스 프록시의 주소 또는 네트워크를 쉼표로 구분(예: `172.18.0.0/16,10.0.0.5`). 이들에게서 온 요청의 `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host` 헤더만 신뢰합니다. 로그인과 페어링 시도를 제한하는 기준이 되는 클라이언트 주소, 로그인 쿠키의 secure 플래그, same-site 검사에 쓰입니다. 설정하지 않으면 이 헤더들은 무시됩니다. |
| `DOWNTIFY_DISCOVERY` | `true` | `false`로 하면 앱이 *이 네트워크에서 찾음*에 서버를 나열하는 데 쓰는 로컬 네트워크 알림(mDNS, `_downtify._tcp`)을 중단합니다. Docker 브리지 네트워크에서는 알림이 어차피 LAN에 닿지 않습니다. [Docker Compose](docker-compose.md#finding-the-server-from-the-apps)를 참고하세요. |
| `DOWNTIFY_TRANSCODE_CACHE_MB` | `2048` | 트랜스코딩된 사본의 캐시(`/data/transcode_cache`)를 유지하는 최대 크기(MB). 가장 오래 재생되지 않은 사본부터 삭제됩니다. |
| `DOWNTIFY_TRANSCODE_CONCURRENCY` | `2` | 앱의 낮은 스트리밍 음질을 위해 동시에 트랜스코딩하는 곡 수. |
| `DOWNTIFY_STREAM_CACHE_MB` | `1024` | 스트리밍된 오디오의 캐시(`/data/stream_cache`)를 유지하는 최대 크기(MB). 가장 오래 재생되지 않은 사본부터 삭제됩니다. 서버를 통한 스트리밍은 브라우저가 직접 YouTube에 접근할 수 없는 곳에서 내려받지 않은 트랙을 재생해 줍니다. |
| `DOWNTIFY_STREAM_CONCURRENCY` | `2` | 동시에 실행할 수 있는 스트림 다운로드 수. |

## 음악 휴지통

[음악 휴지통](../features/music-trash.md)을 참고하세요. 아래 변수 중 하나를 설정하지 않으면 꺼져 있습니다.

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `DOWNTIFY_TRASH` | `false` | `true`로 설정하면 다운로드 폴더에 음악 휴지통이 켜집니다. 곡을 삭제하면 30일 동안 보관되는 휴지통으로 옮겨지며, Downtify가 직접 파일을 옮깁니다. 켜져 있는 동안에는 관리자만 곡을 삭제할 수 있습니다. |
| `DOWNTIFY_TRASH_CONFIG` | _(설정 안 됨)_ | 컨테이너 안에 있는 JSON 파일의 경로로, 휴지통이 다루는 폴더와 워커가 실행되는 위치(`embedded` 또는 `external`)를 지정합니다. `DOWNTIFY_TRASH`보다 우선합니다. 파일을 읽을 수 없으면 서버가 시작되지 않습니다. [설정 파일](../features/music-trash.md#the-configuration-file)을 참고하세요. |

## 상태 확인

이미지에는 [Docker `HEALTHCHECK`](https://docs.docker.com/reference/dockerfile/#healthcheck)가 내장되어 있어 별도의 `--health-cmd`가 필요 없습니다. 30초마다 컨테이너 자체 포트의 `GET /api/health`를 확인합니다(타임아웃 5초, 시작 유예 20초, 컨테이너를 비정상으로 표시하기 전 3회 재시도). `docker ps`와 `docker inspect`에서 결과를 볼 수 있고, Compose의 `condition: service_healthy`나 Watchtower 같은 도구가 이를 활용할 수 있습니다.

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `DOWNTIFY_HEALTHCHECK` | `1` | `0`으로 하면 내장 확인을 끕니다. 그러면 서버에 연결하지 않고 항상 정상으로 보고합니다. 외부/오케스트레이터 수준의 확인(예: Kubernetes liveness probe)만이 컨테이너 상태를 판단하게 하려면 사용하세요. |

```yaml
environment:
  - DOWNTIFY_HEALTHCHECK=0
```

## 안티봇 / YouTube

YouTube는 주기적으로 자동 다운로더를 확인합니다. 기본값이 더 이상 통하지 않을 때를 위한 탈출구가 이 변수들입니다.

| 변수 | 기본값 | 설명 |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(설정 안 됨)_ | `1`로 하면 yt-dlp가 IPv4만 쓰도록 강제합니다. 호스트의 IPv6 주소가 고장났거나 요청 제한에 걸릴 때 유용합니다. |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | 순서대로 시도할 yt-dlp 플레이어 클라이언트의 쉼표 구분 목록. Downtify의 기본 목록은 이미 JavaScript 런타임 없이 동작하는 클라이언트를 우선합니다. 특정 클라이언트가 차단된다는 것을 알 때만 바꾸세요. |
| `DOWNTIFY_YT_PO_TOKEN` | _(설정 안 됨)_ | yt-dlp용 Proof-of-Origin 토큰을 쉼표로 구분하며, 각각 `<client>.<context>+<token>` 형식입니다(예: `mweb.gvs+ABC123`). YouTube가 사용 중인 클라이언트에 PO Token을 요구하기 시작할 때만 필요합니다. |
| `DOWNTIFY_COOKIES_FILE` | _(설정 안 됨)_ | **컨테이너 안의** Netscape 형식 `cookies.txt` 경로. yt-dlp가 실제 브라우저 세션처럼 인증할 수 있게 하며, 선정적/연령 제한 트랙과 YouTube가 로그인 장벽을 둘 때 필요합니다. 웹 UI에서 업로드한 파일보다 우선하고 UI의 해당 섹션을 읽기 전용으로 만듭니다. [YouTube 쿠키](../features/youtube-cookies.md)를 참고하세요. |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(설정 안 됨)_ | 쿠키를 추출할 브라우저 이름(예: `chrome`, `firefox`). 브라우저의 쿠키 저장소가 컨테이너 안에서 접근 가능해야 하므로 Docker에서는 거의 쓸 수 없습니다. |

::: tip 아마 필요 없을 것입니다
웹 UI의 **설정 → YouTube 쿠키**에서 `cookies.txt`를 바로 업로드할 수 있습니다. `/data`에 저장되므로 컨테이너를 업데이트해도 남아 있고, 바인드 마운트나 컨테이너 경로가 필요 없으며, Windows, macOS, Linux에서 똑같이 동작합니다. 위의 변수들은 파일을 직접 관리하고 싶은 배포 환경을 위해 계속 지원됩니다.
:::

## 예시: 안티봇 설정이 있는 Docker Compose

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_FORCE_IPV4=1
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
    restart: unless-stopped
```

## cookies.txt 구하기

[Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)(Chrome)나 [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)(Firefox) 같은 브라우저 확장 프로그램을 사용하세요. 실제 Google 계정에 로그인한 상태로 `youtube.com`에서 내보낸 뒤, **설정 → YouTube 쿠키**에서 업로드하거나 위와 같이 컨테이너에 마운트하세요.

전체 과정은 [YouTube 쿠키](../features/youtube-cookies.md)를, 그래도 다운로드가 실패하면 [문제 해결](../troubleshooting.md)을 참고하세요.

::: warning
`cookies.txt`는 비공개로 보관하세요. Google 계정에 접근할 수 있는 세션 토큰이 들어 있습니다.
:::
