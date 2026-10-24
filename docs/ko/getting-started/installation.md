---
icon: lucide/download
---

# 설치

Downtify를 실행하는 가장 빠른 방법은 `docker run` 명령 하나입니다. 호스트에 Python, Node.js 등 다른 시스템 의존성이 필요 없고, 모든 것이 이미지 안에 들어 있습니다.

## 사전 준비

- [Docker](https://docs.docker.com/get-docker/)가 설치되어 실행 중이어야 합니다

## Docker run

```bash
docker run -d \
  --name downtify \
  -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

`/path/to/music`을 음악을 저장할 디렉터리로 바꾸세요.

컨테이너가 시작되면 브라우저에서 **[http://localhost:8000](http://localhost:8000)**을 여세요.

## 볼륨

| 볼륨 | 용도 |
|--------|---------|
| `/downloads` | 내려받은 오디오 파일 |
| `/data` | 애플리케이션 데이터베이스와 영구 설정 |

두 볼륨 모두 컨테이너를 재시작하거나 업그레이드해도 유지됩니다. `/downloads` 볼륨은 호스트 머신의 아무 디렉터리나 이름 있는 Docker 볼륨이 될 수 있습니다.

## 사용자 지정 포트

Downtify를 다른 호스트 포트로 노출하려면 `-p`의 왼쪽을 바꾸세요.

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # 호스트:컨테이너
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

그런 다음 **[http://localhost:9090](http://localhost:9090)**을 여세요.

## 업데이트

최신 이미지를 받아 컨테이너를 다시 만드세요.

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

음악과 설정은 볼륨에 그대로 보존됩니다.

## 다음 단계

- **[Docker Compose](docker-compose.md)** — 컨테이너를 장기적으로 관리하기 더 쉬운 방법
- **[환경 변수](environment-variables.md)** — 안티봇 동작과 기타 고급 옵션 조정
- **[다운로드 설정](../features/download-settings.md)** — 형식과 비트레이트 선택
