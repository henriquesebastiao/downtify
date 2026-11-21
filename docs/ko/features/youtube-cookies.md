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
      - ./cookies.txt:/cookies.txt
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

쿠키 유지 기능이 교체된 쿠키를 저장할 수 있도록 쓰기 가능하게(`:ro` 없이) 마운트하세요. 읽기 전용 파일도 계속 사용되지만 예전처럼 오래되어 만료됩니다.

이 변수가 설정되면 설정 화면은 쿠키 섹션을 잠긴 상태로 표시하고 업로드와 삭제를 거부합니다. 해당 구성은 배포 환경이 소유하며, Downtify는 자신이 관리하지 않는 파일을 덮어쓰면 안 되기 때문입니다. 웹 UI에서 쿠키를 관리하려면 변수를 제거하고 컨테이너를 다시 만드세요.

`DOWNTIFY_COOKIES_FROM_BROWSER`는 브라우저 프로필에서 쿠키를 직접 읽지만, 브라우저의 쿠키 저장소가 컨테이너 *안에서* 접근 가능해야 하므로 Docker에서는 거의 쓸 수 없습니다.

## 계속 동작하게 유지하기

내보낸 쿠키는 정해진 날짜에 만료되지 않습니다. Google 세션은 계속 바뀌는 쿠키들의 묶음입니다. 쿠키를 내보낸 브라우저 탭은 몇 분마다 `__Secure-1PSIDTS`, `SIDCC` 등을 교체하고, 새 값을 받지 못한 사본은 결국 거부됩니다. 그러면 yt-dlp가 "The provided YouTube account cookies are no longer valid"를 기록합니다. VPN이나 데이터센터 IP에서는 YouTube가 더 엄격해서 몇 시간 만에 이런 일이 생길 수 있습니다.

Downtify는 업로드한 파일의 로그인 상태를 스스로 유지합니다.

- **다운로드할 때마다 새 값을 저장합니다.** yt-dlp는 다운로드마다 파일의 개별 사본을 받고, 끝나면 그동안 YouTube가 바꾼 쿠키를 저장된 `cookies.txt`에 다시 합칩니다. 그 사이 다른 다운로드가 저장한 더 새로운 값은 되돌리지 않습니다.
- **주기적으로 쿠키를 갱신합니다.** 15분마다(`DOWNTIFY_COOKIES_REFRESH_MINUTES`, `0`이면 끔) Downtify는 브라우저와 같은 요청으로 Google에 세션 쿠키 교체를 요청하고, 그 쿠키로 `youtube.com`을 연 뒤 바뀐 내용을 저장합니다. 며칠 동안 아무것도 다운로드하지 않는 서버도 세션이 살아 있습니다.
- **설정 화면에 결과가 보입니다.** **설정 → YouTube 쿠키**에 *로그인됨*, *로그아웃됨*, *계정 없음*(파일에 Google 세션 없이 방문자 쿠키만 있음) 또는 *확인 실패*와 함께 마지막 확인 시각, YouTube가 마지막으로 봇 확인을 요구한 시각이 표시됩니다. *지금 확인*을 누르면 바로 실행됩니다. 새로 업로드한 파일은 저장되고 몇 초 뒤에 확인됩니다.

여전히 직접 해야 하는 일:

- **시크릿 창에서 내보내고 창을 닫으세요.** 시크릿 창에서 YouTube에 로그인하고, 같은 탭에서 `youtube.com/robots.txt`를 연 다음 쿠키를 내보내고 창을 닫습니다. 계속 사용하는 탭은 세션을 스스로 교체해서 Downtify의 사본이 몇 분 안에 로그아웃됩니다. 가능하면 같은 계정을 일반 창에서 동시에 쓰지 마세요.
- **화면에 *로그아웃됨*이 보이면 새 파일을 업로드하세요.** Google은 여전히 세션을 끝낼 수 있습니다(비밀번호 변경, "모든 기기에서 로그아웃", 보안 검토). 로그에도 `YouTube cookies are signed out`이 남습니다.
- 일부 지역에서는 YouTube가 연령 제한 콘텐츠를 제공하기 전에 Google 계정의 전체 본인 인증을 요구합니다. 로그인만으로는 충분하지 않을 수 있습니다.

::: info "Google로 로그인" 버튼이 없는 이유
Downtify는 사용자 대신 Google에 로그인할 수 없습니다. Google은 스크립트와 헤드리스 브라우저 로그인을 차단하고("이 브라우저 또는 앱은 안전하지 않을 수 있습니다"), 2단계 인증과 기기 확인을 요구하며, YouTube는 yt-dlp 같은 서드파티 클라이언트의 OAuth를 더 이상 받지 않습니다. Downtify에 로그인 양식을 둔다는 것은 Google 비밀번호를 Downtify에 넘긴다는 뜻이기도 합니다. 자동화할 수 있는 부분은 내보낸 세션을 살려 두는 것입니다.
:::

::: tip 계정 없이 생기는 봇 확인
"Sign in to confirm you're not a bot"은 쿠키가 없어서가 아니라 IP 주소 때문에 나옵니다. VPN에서 계속 나타난다면 새 쿠키보다 VPN 서버나 출구 국가를 바꾸는 편이 더 효과적인 경우가 많습니다. 많은 다운로드에 쓰인 쿠키는 YouTube가 그 계정을 제한할 가능성도 높이므로, 버려도 되는 계정을 쓰는 편이 안전합니다.
:::

::: warning 파일을 비밀번호처럼 다루세요
`cookies.txt`에는 Google 계정의 유효한 세션 토큰이 들어 있습니다. 이 파일을 읽을 수 있는 사람은 YouTube에서 나처럼 행동할 수 있습니다. Downtify는 파일 시스템이 지원하는 곳에서는 소유자만 접근할 수 있는 권한으로 저장하며, 내용은 API로 절대 노출하지 않습니다. 구성 여부, 크기, 변경 시각만 알려 줍니다. 주 계정을 위험에 빠뜨리고 싶지 않다면 일회용 Google 계정을 쓰세요.
:::
