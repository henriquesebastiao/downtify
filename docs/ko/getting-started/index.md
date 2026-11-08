---
icon: lucide/play
---

# 시작하기

Downtify는 Spotify의 음악을 내려받는 직접 호스팅형 웹 앱입니다. API 키도, 계정도, Premium 구독도 필요 없습니다. 모든 것이 하나의 Docker 컨테이너 안에서 실행됩니다.

## 준비물

- **Docker**(또는 Docker Compose) — 호스트 머신에 필요한 유일한 요구 사항
- 인터넷에 연결된 머신
- 음악을 저장할 볼륨/디렉터리

## 설치 방법 고르기

<div class="doc-cards">

- <DocIcon name="docker" /> **Docker run**

  가장 빠르게 시작하는 방법. 명령 하나로 1분 안에 실행됩니다.

  [설치 →](installation.md)

- <DocIcon name="file-code" /> **Docker Compose**

  오래 운영할 환경에 권장합니다. 업데이트와 관리가 더 쉽습니다.

  [Docker Compose →](docker-compose.md)

- <DocIcon name="house" /> **원클릭 설치**

  Umbrel, CasaOS, HomeDock OS를 쓰시나요? 각 플랫폼의 앱 스토어에서 바로 설치하세요.

  [원클릭 설치 →](one-click.md)

</div>

## 다음 단계

Downtify가 실행되면 브라우저에서 [http://localhost:8000](http://localhost:8000)을 여세요. 검색창에 Spotify 트랙, 앨범 또는 재생목록 URL을 붙여넣고 **다운로드**를 누르면 됩니다.

[다운로드 설정](../features/download-settings.md), [재생목록 모니터](../features/playlist-monitor.md), [내장 플레이어](../features/player.md) 등 나머지 문서도 살펴보세요.
