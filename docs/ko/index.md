---
layout: home
title: Downtify
titleTemplate: "직접 호스팅하는 Spotify 다운로더 겸 음악 플레이어"
description: "플레이어가 내장된 셀프 호스팅 Spotify 다운로더. Spotify, YouTube Music, Deezer, SoundCloud 링크를 붙여넣으면 태그가 정리된 MP3나 FLAC 파일을 받을 수 있습니다. API 키가 필요 없습니다."
icon: lucide/house
hero:
  eyebrow: 직접 호스팅하는 음악 다운로더
  headline:
    - 링크를 붙여넣고,
    - 음악을 받으세요.
  lead: 플레이어가 내장된, 직접 호스팅하는 음악 다운로더. Spotify, YouTube Music, Deezer, SoundCloud 링크를 붙여넣으면 브라우저, 휴대폰, 미디어 서버에서 바로 재생할 수 있도록 태그가 완벽하게 정리된 라이브러리가 생깁니다.
  note: Spotify 계정도, API 키도, Premium도 필요 없습니다.
  actions:
    - text: 시작하기
      link: /ko/getting-started/installation/
      primary: true
    - text: GitHub 소스 코드
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: 릴리스
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker 풀 수
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: GitHub 스타
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: 라이선스
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: '44초로 보는 Downtify: 재생목록 링크를 붙여넣고, 클릭 한 번으로 내려받고, 동기화를 유지하고, 동기화 가사와 함께 데스크톱과 휴대폰에서 재생합니다.'
why:
  - icon: link
    title: 링크 하나면 충분합니다
    text: Spotify, YouTube Music, Deezer, SoundCloud의 곡, 앨범, 재생목록 전체 또는 아티스트를 붙여넣거나, 듣고 싶은 것을 그냥 입력하세요. Downtify가 오디오를 찾아 가져옵니다.
    link: /ko/how-it-works/
  - icon: tag
    title: 간직할 만한 파일
    text: 모든 파일에 커버, 참여한 모든 아티스트, 앨범, 연도, 트랙 번호, 그리고 가사(있으면 시간 동기화)가 들어갑니다. MP3, FLAC, M4A, OGG, Opus 중에서 고르거나 소스 오디오를 그대로 받을 수 있습니다.
    link: /ko/features/download-settings/
  - icon: music
    title: 나만의 스트리밍 서비스
    text: 동기화 가사, 노래방, 대기열, 좋아요 표시한 곡, 재생목록, 팟캐스트를 갖춘 브라우저용 완전한 플레이어. Android와 iOS 앱으로 라이브러리를 오프라인으로도 들고 다닐 수 있습니다.
    link: /ko/features/player/
  - icon: radar
    title: 설정하고 잊어버리세요
    text: 재생목록과 아티스트를 지켜보세요. 새 곡과 새 발매작이 원하는 주기로 저절로 내려받아집니다.
    link: /ko/features/playlist-monitor/
  - icon: server
    title: 홈 서버를 위해 만들어졌습니다
    text: amd64와 arm64용 Docker 이미지 하나, SQLite 또는 PostgreSQL, 선택적 통합 로그인(SSO)을 갖춘 가족 모두의 계정, 그리고 Jellyfin, Navidrome, Plex가 인식하는 재생목록.
    link: /ko/getting-started/
  - icon: shield
    title: 아무 조건 없이
    text: Spotify API 키도, 개발자 계정도, Premium도 필요 없습니다. 앱에는 광고도, 사용 통계도, 유료 기능도 없습니다. 자유 오픈 소스입니다.
    link: /ko/contributing/
showcase:
  - shot: now-playing
    label: 현재 재생 중
    caption: 가사가 커버와 다음 곡 옆에서 한 줄씩 노래를 따라갑니다.
    alt: 전체 화면의 현재 재생 중 화면. 앨범 커버, 현재 줄이 강조된 동기화 가사, 대기열이 보입니다.
  - shot: karaoke
    label: 노래방
    caption: 각 줄을 부르는 동안 채워지는 큰 가사. 두 번째 화면에서 열 수 있습니다.
    alt: 커버 색상으로 움직이는 배경 위에 큰 가사가 채워지는 노래방 화면.
  - shot: home
    label: 홈
    caption: 링크를 붙여넣거나 새로운 것을 검색하고, 하던 곳에서 이어서 들으세요.
    alt: 링크를 붙여넣거나 검색하는 입력창, 라이브러리 통계, 재생 중인 앨범, 최근 추가된 앨범이 있는 홈 페이지.
  - shot: library
    label: 라이브러리
    caption: 앨범, 아티스트, 재생목록, 트랙을 원하는 대로 정렬하고 필터링합니다.
    alt: 앨범 커버 그리드와 앨범, 아티스트, 재생목록, 트랙 탭이 있는 라이브러리 페이지.
  - shot: playlist
    label: 재생목록
    caption: 고유한 커버를 가진 나만의 재생목록. 재생하고, 공유하고, ZIP으로 내려받으세요.
    alt: 커버, 버튼, 앨범·형식·발매일이 표시된 곡 목록이 있는 재생목록 페이지.
  - shot: phones
    label: 휴대폰에서
    caption: 같은 앱을 휴대폰에서 사용하세요. 브라우저에서 설치할 수 있습니다.
    alt: 세 대의 휴대폰에 표시된 Downtify의 홈 페이지, 현재 재생 중 화면, 라이브러리.
pipeline:
  - icon: link
    title: 링크 붙여넣기
    text: Spotify, YouTube Music, Deezer 또는 SoundCloud. 곡 이름만 입력해도 됩니다.
  - icon: search
    title: 오디오 찾기
    text: 길이로 확인한 YouTube Music의 가장 가까운 결과. 원하면 다른 소스도 사용합니다.
  - icon: download
    title: 내려받고 태그 입력
    text: yt-dlp와 ffmpeg이 가져오고, 커버·가사·태그가 파일 안에 들어갑니다.
  - icon: music
    title: 어디서나 재생
    text: 브라우저, 휴대폰, 또는 Jellyfin, Navidrome, Plex에서.
quickStart:
  - text: 설치 가이드
    link: /ko/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /ko/getting-started/docker-compose/
  - text: 원클릭 설치
    link: /ko/getting-started/one-click/
apps:
  - icon: smartphone
    title: Android용 Downtify
    text: 공식 앱입니다. 네트워크에서 서버를 찾아 Wi-Fi에서는 원본 품질로, 모바일 데이터에서는 더 작은 품질로 스트리밍하고, 곡을 오프라인으로 보관하며, Android Auto에서도 동작합니다. 아직 테스트 중이며 GitHub Releases와 Obtainium에서 받을 수 있습니다.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: iOS용 Downtify
    text: 커뮤니티 멤버가 iPhone과 iPad(iOS 17 이상)용으로 만든 앱으로, 오프라인 곡과 잠금 화면 컨트롤을 지원합니다. 공개 베타는 TestFlight에 있습니다.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: GitHub에서 스타 주기
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: 후원하기
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: 번역하기
    link: /ko/features/internationalization/
    icon: languages
  - text: 기여하기
    link: /ko/contributing/
    icon: git-pull-request
---

## 왜 Downtify인가

<HomeHighlights :items="$frontmatter.why" />

## 자세히 보기

<HomeShowcase :items="$frontmatter.showcase" />

## 작동 방식

Downtify는 Spotify API 키가 필요 없고 Spotify에서 아무것도 내려받지 않습니다. 링크가 가리키는 내용을 공개된 소스에서 읽고, 길이가 가장 잘 맞는 YouTube Music 오디오를 골라 `yt-dlp`로 내려받고, `ffmpeg`로 변환하고, `mutagen`으로 태그를 입력합니다. 이 모든 과정이 Docker 컨테이너 하나에서 이루어집니다. 잘 맞는 결과가 없으면 YouTube가 대신하고, SoundCloud, Soulseek, Deemix는 켜 두면 함께 사용됩니다. [각 단계 자세히 보기](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## 붙여넣을 수 있는 것

| 소스          | 지원 항목                          | 예                                  |
| ------------- | ---------------------------------- | ----------------------------------- |
| Spotify       | 트랙, 앨범, 재생목록, 아티스트     | `open.spotify.com/playlist/…`       |
| YouTube Music | 곡, 앨범, 재생목록, 아티스트       | `music.youtube.com/playlist?list=…` |
| YouTube       | 동영상                             | `youtube.com/watch?v=…`             |
| Deezer        | 트랙, 앨범, 재생목록, 아티스트     | `deezer.com/album/…`                |
| SoundCloud    | 트랙                               | `soundcloud.com/artist/track`       |
| 검색          | 입력하고 싶은 무엇이든             | `The Night Owls Do I Still Recall`  |
| CSV           | 라이브러리 내보내기 파일           | Soundiiz, TuneMyMusic, Exportify    |

## 할 수 있는 모든 것

기능마다 모든 옵션을 설명하는 페이지가 따로 있습니다. [모든 기능 한눈에 보기](features/index.md).

<HomeFeatures />

## 1분 만에 실행

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

[`localhost:8000`](http://localhost:8000)을 열고 **admin** 계정과 **downtify** 비밀번호로 로그인한 뒤 링크를 붙여넣으세요. 이 비밀번호는 바로 **설정 → 일반**에서 바꾸세요. 음악은 태그까지 갖춘 채 `/path/to/music`에 저장됩니다.

<HomeActions :actions="$frontmatter.quickStart" />

## 자주 묻는 질문

::: details Spotify 계정, Premium, API 키가 필요한가요?
아니요. Downtify는 트랙, 앨범, 재생목록 정보를 Spotify의 공개 임베드(embed) 페이지에서 읽으므로 어떤 자격 증명도 필요 없고, 오디오는 절대 Spotify에서 오지 않습니다. [작동 방식](how-it-works.md)을 참고하세요.
:::

::: details 오디오는 어디서 오고, 음질은 어떤가요?
기본적으로 YouTube Music에서 곡 길이가 가장 잘 맞는 결과를 가져오고, 없으면 YouTube를 사용합니다. MP3, FLAC, M4A, OGG, Opus를 원하는 비트레이트로 고르거나, 소스의 가장 좋은 오디오를 재인코딩 없이 그대로 받을 수 있습니다. 무손실 파일은 직접 추가하는 소스에서 옵니다: 원본 형식을 그대로 유지하는 자신의 [Soulseek(slskd)](features/slskd-navidrome.md) 서버, 또는 [Deemix](features/deemix.md) 서버입니다. [다운로드 설정](features/download-settings.md)을 참고하세요.
:::

::: details Jellyfin, Navidrome, Plex와 함께 쓸 수 있나요?
네. 파일은 미디어 서버가 기대하는 방식으로 태그가 입력되고 `아티스트/앨범/` 폴더에 저장되며, 모든 재생목록에는 이들이 인식하는 표준 M3U 파일이 생깁니다. Navidrome은 재생목록 동기화와 Deezer 기반 별점도 받을 수 있습니다. [파일 정리](features/file-organization.md)와 [M3U 내보내기](features/m3u-export.md)를 참고하세요.
:::

::: details Raspberry Pi나 NAS에서 돌아가나요?
이미지는 `amd64`와 `arm64`용으로 제공되며, Umbrel, CasaOS, HomeDock OS에서 클릭 한 번으로 설치할 수 있습니다. [원클릭 설치](getting-started/one-click.md)를 참고하세요.
:::

::: details YouTube가 "Sign in to confirm you're not a bot"이라고 합니다. 어떻게 하나요?
**설정 → YouTube 쿠키**에서 `cookies.txt`를 업로드하세요. 이후 Downtify가 그 세션의 로그인 상태를 스스로 유지합니다. 그래도 YouTube가 제한하면 _다운로드 간격_을 늘리고 _동시 다운로드 수_를 줄인 뒤 `DOWNTIFY_FORCE_IPV4=1`을 시도해 보세요. [문제 해결](troubleshooting.md)과 [YouTube 쿠키](features/youtube-cookies.md)를 참고하세요.
:::

## 어디든 가지고 다니세요

<HomeHighlights :items="$frontmatter.apps" />

다른 클라이언트도 같은 API를 사용할 수 있습니다. [모바일 클라이언트 계약](mobile-client-contract.md)을 참고하세요.

<div class="home-cta">

## 공개적으로 만들어집니다

Downtify는 자유 오픈 소스입니다. 35명이 넘는 사람이 코드에 기여했고, 커뮤니티 번역가들이 12개 언어로 옮겼으며, 많은 기능이 누군가 이슈로 올린 아이디어에서 시작되었습니다. 서버에 자리를 잡았다면 GitHub에서 스타를 주거나, 직접 서비스를 운영하는 친구에게 알려 주거나, 개발을 후원해 주세요. 매 릴리스에 들어가는 시간을 충당하는 데 도움이 됩니다.

<HomeActions :actions="$frontmatter.community" />

</div>
