---
icon: lucide/file-code
---

# Docker Compose

Docker Compose는 오래 운영하는 홈 서버 환경에서 Downtify를 실행하는 데 권장되는 방법입니다. 업데이트, 백업, 설정 변경이 쉬워집니다.

## 최소 구성

`docker-compose.yml` 파일을 만드세요.

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped

volumes:
  downtify_data:
```

실행합니다.

```bash
docker compose up -d
```

**[http://localhost:8000](http://localhost:8000)**을 여세요.

## slskd(Soulseek)와 함께

[slskd를 음원 출처로](../features/slskd-navidrome.md) 쓰려면 slskd의 다운로드 폴더도 Downtify에 마운트하세요. slskd 컨테이너가 기록하는 **같은 호스트 폴더**여야 합니다.

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

그런 다음 **설정 → 음원 출처 → slskd**에서 slskd를 켜고, URL(두 컨테이너가 Docker 네트워크를 공유한다면 예: `http://slskd:5030`)과 API 키를 입력하고, 다운로드 폴더를 `/slskd`로 설정하세요.

## 기존 음악 폴더

호스트에 이미 가지고 있는 컬렉션을 라이브러리가 인식하게 하려면 같은 방식으로 [마운트](../features/external-library.md)하고 **설정 → 라이브러리**에 **컨테이너** 경로를 입력하세요.

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## 앱에서 서버 찾기

[모바일 앱](../features/mobile-apps.md#finding-the-server-on-your-network)은 mDNS로 네트워크의 Downtify 서버를 나열합니다. Docker의 기본 브리지 네트워크에서는 그 알림이 Docker 밖으로 나가지 않아 휴대폰에서 보이지 않습니다. 목록에 나타나게 하려면 컨테이너를 호스트 네트워크에서 실행하세요. 그러면 `ports:` 매핑이 더 이상 적용되지 않고 Downtify가 `DOWNTIFY_PORT`에서 직접 수신합니다.

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    network_mode: host
    environment:
      - DOWNTIFY_PORT=8000
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

그렇지 않으면 앱에 서버 주소(`http://<호스트 IP>:8000`)를 직접 입력하면 됩니다. 그 밖의 어떤 것도 검색에 의존하지 않습니다.

## 사용자 지정 포트

8000번 포트가 이미 사용 중이면 다른 호스트 포트를 매핑하고, 컨테이너가 내부에서 같은 포트로 수신하도록 `DOWNTIFY_PORT` 환경 변수를 설정하세요.

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '9090:30321'
    environment:
      - DOWNTIFY_PORT=30321
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

`DOWNTIFY_PORT`를 설정하는 대신 **설정 → 서버 → 포트**에서 포트를 고를 수도 있습니다(`DOWNTIFY_PORT`가 설정되어 있으면 설정보다 우선합니다). 기본 브리지 네트워크에서는 `ports:` 매핑을 같은 포트로 바꾸고 컨테이너를 다시 만드세요. [포트 변경](../features/server.md#changing-the-port)을 참고하세요.

## 사용자 지정 DNS와 함께(권장)

일부 인터넷 사업자와 기업 네트워크는 YouTube를 차단합니다. 명시적인 DNS 리졸버를 추가하면 안정성이 좋아집니다.

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    dns:
      - 1.1.1.1
      - 1.0.0.1
    restart: unless-stopped
```

## 업데이트

```bash
docker compose pull
docker compose up -d
```

음악과 설정은 볼륨에 그대로 보존됩니다.

## 볼륨

| compose 파일 안의 경로 | 용도 |
|------------------------------|---------|
| `./downloads:/downloads` | 내려받은 오디오 파일(로컬 디렉터리) |
| `downtify_data:/data` | 애플리케이션 데이터베이스와 설정(이름 있는 볼륨) |

직접 관리하고 싶다면 이름 있는 볼륨을 로컬 경로(`./data:/data`)로 바꿔도 됩니다.
