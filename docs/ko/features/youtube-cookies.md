---
icon: lucide/cookie
---

# YouTube 쿠키

Downtify는 오디오를 YouTube에서 가져옵니다. 대부분은 익명으로도 잘 동작하지만, 항상 그런 것은 아닙니다.

- **선정적/연령 제한 트랙.** YouTube는 이런 트랙을 로그인한 성인 계정에만 제공합니다. 쿠키가 없으면 다운로드가 실패합니다.
- **봇 확인.** 데이터센터 IP(VPS, 일부 VPN)에서는 YouTube가 가끔 오디오 대신 "봇이 아님을 확인하려면 로그인하세요"라고 응답합니다.

`cookies.txt`를 제공하면 둘 다 해결됩니다. 그러면 yt-dlp가 로그인한 브라우저 세션처럼 YouTube와 통신합니다.

## cookies.txt 업로드(권장)

1. 쿠키 내보내기 확장 프로그램을 설치합니다: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)(Chrome/Edge) 또는 [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)(Firefox)
2. **Google 계정에 로그인한 상태로** `youtube.com`을 열고 그 사이트의 쿠키를 내보냅니다. 파일은 **Netscape** 형식이어야 합니다
3. Downtify에서 **설정**(⚙️) → **YouTube 쿠키** → **cookies.txt 업로드**를 엽니다

파일은 업로드할 때 검증됩니다. Netscape 쿠키 저장소 형식이 아닌 파일은 이후의 모든 다운로드를 조용히 망가뜨리는 대신 즉시 거부됩니다. `youtube.com`이나 `google.com` 쿠키가 하나도 없으면 경고가 표시되는데, 보통 잘못된 탭에서 내보냈다는 뜻이기 때문입니다.

업로드한 뒤에는 같은 화면에서 **교체**(다른 파일 업로드)하거나 **삭제**할 수 있습니다.

::: tip 플랫폼에 상관없이 쓸 수 있는 방법입니다
웹 UI로 업로드하는 방식은 바인드 마운트도, 파일 경로도, 셸도 필요 없습니다. 그래서 컨테이너에 `cookies.txt`를 마운트하기가 악명 높게 까다로운 Windows용 Docker Desktop에서도 동작합니다.
:::

## 저장되는 위치

업로드한 파일은 Downtify의 데이터 디렉터리(기본 `/data`) 안에 `cookies.txt`로 기록됩니다. `settings.json`과 재생목록 모니터 데이터베이스가 있는 바로 그 볼륨입니다. 그래서 **컨테이너를 업데이트해도 남아 있습니다**. `/data`가 이름 있는 볼륨이나 바인드 마운트로 유지되는 한, 새 이미지를 받아 컨테이너를 다시 만들어도 쿠키가 유지됩니다.

## 대신 환경 변수 사용하기

이미 있던 [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube) 변수도 여전히 동작하며 **우선합니다**.

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

이 변수가 설정되면 설정 화면은 쿠키 섹션을 잠긴 상태로 표시하고 업로드와 삭제를 거부합니다. 해당 구성은 배포 환경이 소유하며, Downtify는 자신이 관리하지 않는 파일을 덮어쓰면 안 되기 때문입니다. 웹 UI에서 쿠키를 관리하려면 변수를 제거하고 컨테이너를 다시 만드세요.

`DOWNTIFY_COOKIES_FROM_BROWSER`는 브라우저 프로필에서 쿠키를 직접 읽지만, 브라우저의 쿠키 저장소가 컨테이너 *안에서* 접근 가능해야 하므로 Docker에서는 거의 쓸 수 없습니다.

## 계속 동작하게 유지하기

- 쿠키는 만료됩니다. 연령 제한 다운로드가 다시 실패하기 시작하면 새 파일을 내보내 교체하세요.
- 나중에 닫는 **시크릿/비공개 창**에서 내보내면 더 오래가는 세션이 만들어집니다. 일반 창을 닫으면 내보낸 세션이 무효화될 수 있기 때문입니다.
- 일부 지역에서는 YouTube가 연령 제한 콘텐츠를 제공하기 전에 Google 계정의 완전한 본인 확인을 요구합니다. 로그인만으로는 항상 충분하지 않습니다.

::: warning 파일을 비밀번호처럼 다루세요
`cookies.txt`에는 Google 계정의 유효한 세션 토큰이 들어 있습니다. 이 파일을 읽을 수 있는 사람은 YouTube에서 나처럼 행동할 수 있습니다. Downtify는 파일 시스템이 지원하는 곳에서는 소유자만 접근할 수 있는 권한으로 저장하며, 내용은 API로 절대 노출하지 않습니다. 구성 여부, 크기, 변경 시각만 알려 줍니다. 주 계정을 위험에 빠뜨리고 싶지 않다면 일회용 Google 계정을 쓰세요.
:::
