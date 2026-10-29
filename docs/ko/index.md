---
layout: home
title: Downtify
titleTemplate: 직접 호스팅하는 음악 다운로더
description: 직접 호스팅하는 음악 다운로더. Spotify 링크를 붙여넣으면 태그가 완벽하게 입력된 오디오 파일을 받을 수 있습니다 — API 키도, 계정도, 번거로움도 없습니다.
icon: lucide/house
hero:
  eyebrow: 직접 호스팅하는 음악 다운로더
  lead:
    - 내 컴퓨터에서 직접 호스팅할 수 있는 음악 다운로더.
    - Spotify 링크를 넣으면 태그가 입력된 오디오 파일을 받습니다. 계정도, API 키도, Premium도 필요 없습니다.
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
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: 라이선스
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: 메타데이터
  - title: YouTube Music
    text: 오디오 매칭
  - title: yt-dlp · ffmpeg · mutagen
    text: 다운로드 및 태그
highlights:
  - icon: eye
    title: 재생목록 모니터
    text: 재생목록을 지켜보다가 새 트랙이 추가되면 조용히 내려받습니다.
    link: /ko/features/playlist-monitor/
  - icon: sliders-horizontal
    title: 다섯 가지 형식
    text: MP3, FLAC, M4A, OGG, OPUS — 원하는 비트레이트로.
    link: /ko/features/download-settings/
  - icon: mic-vocal
    title: 가사 내장
    text: lrclib에서 가져온 일반 가사와 시간 동기화 가사를 파일에 포함합니다.
    link: /ko/features/lyrics/
  - icon: headphones
    title: 웹 플레이어
    text: 셔플, 반복, 볼륨, 앨범 커버 — 브라우저에서 바로.
    link: /ko/features/player/
  - icon: list-music
    title: M3U 내보내기
    text: Jellyfin, Navidrome, Plex가 자동으로 인식하는 표준 EXTM3U 파일.
    link: /ko/features/m3u-export/
  - icon: folder
    title: 라이브러리 구성
    text: 한 폴더에 모두 두거나 아티스트별 폴더로 — 미디어 서버가 선호하는 방식으로.
    link: /ko/features/file-organization/
  - icon: import
    title: CSV 라이브러리 가져오기
    text: Soundiiz, TuneMyMusic, Exportify의 내보내기 파일을 가져와 전체를 대기열에 넣습니다.
    link: /ko/features/library-import/
quickStart:
  - text: 설치 가이드
    link: /ko/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /ko/getting-started/docker-compose/
---

## 실제로 작동하는 방식

Spotify 공식 API는 다운로드를 Premium 구독 뒤에 묶어 둡니다. Downtify는 옆문을 이용합니다. Spotify가 이미 공개 임베드 페이지에 노출하는 메타데이터를 읽고, YouTube Music에 가장 비슷한 오디오를 요청하고, 파일을 `yt-dlp`와 `ffmpeg`에 넘기고, `mutagen`으로 올바른 태그를 기록합니다. 전체 파이프라인이 하나의 Docker 컨테이너 안에서 돌아갑니다.

<HomePipeline :steps="$frontmatter.pipeline" />

## 붙여넣을 수 있는 것

|                    |                                    |
| ------------------ | ---------------------------------- |
| Spotify 트랙       | `open.spotify.com/track/…`         |
| Spotify 앨범       | `open.spotify.com/album/…`         |
| Spotify 재생목록   | `open.spotify.com/playlist/…`      |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| 자유 입력 검색     | `The Night Owls Do I Still Recall` |

## 주요 기능

<HomeHighlights :items="$frontmatter.highlights" />

## 명령 하나면 끝

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

[`localhost:8000`](http://localhost:8000)을 열고 링크를 붙여넣은 뒤 다운로드를 누르세요. 파일은 태그가 이미 입력된 채로 `/path/to/music`에 저장됩니다.

<HomeActions :actions="$frontmatter.quickStart" />
