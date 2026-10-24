---
icon: lucide/cog
---

# 작동 방식

Downtify의 다운로드 파이프라인은 세 단계로 이루어집니다.

```
Spotify embed  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
  (metadata)         (audio match)          (download & tag)
```

## 1. 메타데이터 — Spotify 임베드 페이지 읽기

Spotify URL을 붙여넣으면 Downtify는 해당 트랙, 앨범, 재생목록의 공개 `open.spotify.com/embed` 페이지를 가져옵니다. Spotify 계정, API 키, Premium 구독이 필요 없습니다. 임베드 페이지는 누구나 접근할 수 있습니다.

**트랙**의 경우 임베드는 제목, 아티스트, 앨범 이름, 발매 연도, 길이, 커버 이미지 URL을 돌려줍니다.

**앨범과 재생목록**의 경우 트랙 목록을 돌려줍니다. 재생목록 임베드는 대략 50~100개 항목으로 제한되므로, Downtify는 수백 곡짜리 재생목록도 처리할 수 있도록 Spotify의 익명 `api.spotify.com` 엔드포인트에서 페이지 단위로 전체 목록도 요청합니다.

::: info 트랙별 메타데이터 보강
임베드의 재생목록 항목에는 발매 연도가 없고, 각 트랙의 앨범 커버 대신 재생목록 커버가 쓰입니다. [재생목록 모니터](features/playlist-monitor.md)에서는 다운로드 전에 올바른 커버와 연도를 얻기 위해 새 트랙을 하나씩 다시 가져옵니다.
:::

## 2. 오디오 매칭 — YouTube Music, 그다음 YouTube

Downtify는 [`ytmusicapi`](https://ytmusicapi.readthedocs.io/)로 YouTube Music에서 가장 잘 맞는 오디오를 검색합니다. 검색어는 트랙 제목과 아티스트 이름으로 만듭니다.

결과는 제목이 원본 제목과 비슷하고 아티스트가 하나 이상 겹칠 때만 받아들입니다. Spotify의 대시 방식 버전 접미사와 YouTube Music의 괄호 방식은 같은 것으로 취급하고(`Tubarões - Ao Vivo`는 `Tubarões (Ao Vivo)`와 일치), YouTube Music이 한 항목에 묶어 둔 아티스트 표기(`A, B, and C`)는 비교 전에 나눕니다. 아티스트 이름 앞의 "The"는 무시하고(`Eden Project`는 `The Eden Project`와 일치), 제목은 나머지 부분이 다른 버전을 가리키지 않는 한 업로드 제목의 ` - `로 구분된 한 부분과 일치할 수 있습니다(`くちづけDiamond - Kuchizuke Diamond`, `Game OST - Song Title - Artist`). 노래방, 커버, 연주곡, 스피드업/슬로우, 라이브(`Ao Vivo`/`En Vivo` 포함), 어쿠스틱, 리믹스, 다른 언어 버전(예: `(Spanish Version)`)은 원본 트랙 자체가 그 버전이 아닌 한 거부합니다. 남은 결과 중에서는 길이가 Spotify와 가장 가까운 것이 이기며, 앨범 이름이 일치하면 가산점이 있습니다. 어떤 결과도 조건에 맞지 않으면 단어 순서를 바꿔(`<아티스트> <제목>` 대신 `<제목> <아티스트>`) 검색을 반복합니다. YouTube Music은 단어 순서에 따라 결과 순위가 달라지며, 어떤 곡은 한 방향으로만 상위에 나타나기 때문입니다. 그래도 아무것도 찾지 못하고 앨범을 알고 있다면 앨범의 트랙 목록을 직접 훑습니다.

### 일반 YouTube로 대체

일부 곡은 YouTube Music에 없거나 다른 녹음으로만 존재합니다. 그래서 다음 경우에는 일반 YouTube도 검색합니다.

- YouTube Music에 **받아들일 만한 결과가 없을 때**
- 가장 좋은 결과의 길이가 Spotify와 **10초 넘게** 다를 때 — 다른 녹음(예: 같은 제목의 더빙 버전)일 가능성이 높다는 강한 신호입니다.

일반 YouTube 결과도 같은 제목, 아티스트, 버전 검사를 거치며, Spotify 길이와 30초를 넘게 차이 나는 결과는 절대 받아들이지 않습니다. YouTube 결과는 길이가 엄격하게 더 가까울 때만 약한 YouTube Music 결과를 대체하며, 그렇지 않으면 카탈로그 업로드의 음질이 보통 가장 깨끗하므로 YouTube Music 결과를 유지합니다.

두 사이트 모두 받아들일 만한 결과가 없으면 엉뚱한 곡을 내려받는 대신 `Could not find a YouTube match for '<title>'` 오류로 실패합니다.

YouTube URL을 직접 입력한 경우 이 단계는 건너뛰며, Downtify는 그 영상을 그대로 내려받습니다.

::: info Deezer 링크
붙여넣은 Deezer 트랙/앨범/재생목록/아티스트 링크(`deezer.com/track/…`)는 Spotify 링크와 같은 방식으로 동작합니다. Deezer의 공개 REST API가 제목, 아티스트, 앨범, 커버를 제공하고, 내려받기 전에 모든 트랙을 YouTube에서 전체 스트리밍할 수 있으며, 같은 단계가 YouTube Music/YouTube에서 매칭합니다. Downtify에는 Deezer API가 이미 돌려주는 것 이상의 자체 Deezer 디스코그래피 해석기가 없으므로, Deezer 링크는 다운로드되고(재생목록이면) 자체 M3U와 커버를 갖지만 [재생목록 모니터](features/playlist-monitor.md)로 지켜볼 수는 없습니다.
:::

## 3. 다운로드와 태그 — yt-dlp + ffmpeg + mutagen

### 다운로드

[yt-dlp](https://github.com/yt-dlp/yt-dlp)가 YouTube에서 오디오를 내려받습니다. Downtify는 YouTube의 봇 탐지 도전을 피하기 위해 여러 플레이어 클라이언트(`ios`, `android`, `web_embedded`, `mweb`, `web`, `tv`)를 순서대로 시도하도록 설정합니다. 고급 안티봇 옵션은 [환경 변수](getting-started/environment-variables.md)를 참고하세요.

### 변환

[ffmpeg](https://ffmpeg.org/)가 원본 오디오를 선택한 형식(MP3, FLAC, M4A, OGG, OPUS)과 선택한 비트레이트로 변환합니다.

### 태그 입력

[mutagen](https://mutagen.readthedocs.io/)이 변환된 파일에 메타데이터를 기록합니다.

| 태그 | 기록 여부 |
|-----|---------|
| 제목 | 예 |
| 아티스트 | 예 |
| 앨범 | 예 |
| 연도 | 예 |
| 앨범 커버(JPEG) | 예 |
| 가사(일반 + 동기화) | 예, lrclib이 결과를 돌려주면 |
| 성인 콘텐츠 표시 | 예, 곡이 선정적(explicit)으로 표시되어 있으면([성인 콘텐츠 표시](features/explicit-marker.md) 참고) |

실제로 쓰이는 ID3/Vorbis/MP4 태그는 출력 형식에 따라 다릅니다. 가사가 포함되는 방식은 [가사](features/lyrics.md)를 참고하세요.

## 실시간 진행 상황

Downtify는 **WebSocket** 연결(`/api/ws`)로 다운로드 진행 상황을 브라우저에 스트리밍합니다. yt-dlp가 진행 상황을 보고할 때마다 서버가 퍼센트와 상태 업데이트를 연결된 모든 클라이언트에 전송합니다. 그래서 폴링이나 페이지 새로고침 없이 진행률 표시줄이 실시간으로 움직이는 것을 볼 수 있습니다.

## 파일 이름과 정리

출력 파일 이름은 설정에서 지정한 템플릿(기본값 `{artists} - {title}`)으로 만들어집니다. 파일 이름에 쓸 수 없는 문자는 제거됩니다.

*아티스트별로 정리*가 켜져 있으면 파일은 대표 아티스트 이름의 하위 폴더에 놓입니다. 그렇지 않으면 개별 트랙은 다운로드 디렉터리의 최상위에, 재생목록/앨범 트랙은 재생목록 또는 앨범별 하위 폴더에 놓입니다.
