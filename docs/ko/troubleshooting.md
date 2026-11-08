---
icon: lucide/life-buoy
---

# 문제 해결

흔한 문제와 해결 방법입니다. 다운로드 실패의 대부분은 처음 두 항목 중 하나로 귀결됩니다.

## 선정적인 콘텐츠가 있는 트랙이 다운로드되지 않음

**증상** — 다운로드가 실패하고 대기열에 트랙이 연령 제한이라는 메시지가 표시되거나, (이전 버전에서는) 다음과 같은 원시 오류가 표시됩니다.

```
Error: ERROR: [youtube] <id>: Sign in to confirm your age.
This video may be inappropriate for some users.
```

**원인** — YouTube는 연령 제한(선정적) 트랙을 로그인한 성인 계정에만 제공합니다. Downtify는 기본적으로 익명으로 내려받으므로 YouTube가 거부합니다.

**해결** — YouTube 쿠키를 제공하세요: **설정**(⚙️) → **YouTube 쿠키** → **cookies.txt 업로드**. 파일을 내보내는 방법은 [YouTube 쿠키](features/youtube-cookies.md)를 참고하세요.

쿠키를 설정했는데도 실패한다면 쿠키가 오래되었거나 계정 자체가 Google의 연령 확인을 마치지 않은 것입니다. 인증된 계정으로 로그인한 브라우저에서 새 파일을 내보내 다시 업로드하세요.

## 다운로드가 실패하거나, 시간 초과되거나, 시작되지 않음

**증상** — 평범해 보이는 트랙에서도 다운로드가 실패하며, 가끔 "봇이 아님을 확인하려면 로그인하세요" 또는 형식/추출 오류가 나타납니다.

**원인** — YouTube는 자동화로 보이는 요청을 제한하고 확인을 요구합니다. VPS나 VPN 뒤에서는 가정용 연결보다 훨씬 흔합니다.

**해결** — 효과가 큰 순서대로:

1. **`cookies.txt`를 업로드하세요**([YouTube 쿠키](features/youtube-cookies.md)). 인증된 세션은 확인을 요구받는 일이 훨씬 적습니다. 가장 효과적인 방법 하나입니다.
2. **다운로드 사이에 간격을 두세요** — **설정** → *다운로드 간격*(5~15초를 시도)과 *동시 다운로드 수*를 낮추세요. 재생목록 전체로 YouTube를 한꺼번에 두드리면 요청 제한이 걸립니다.
3. **IPv4를 강제하세요** — 호스트가 IPv6를 알리지만 실제로 라우팅하지 못한다면 `DOWNTIFY_FORCE_IPV4=1`을 설정하세요(DNS/`EAI_AGAIN` 오류로 나타납니다).
4. **이미지를 업데이트하세요** — `docker compose pull && docker compose up -d`. YouTube는 방어 방식을 자주 바꾸며, 릴리스마다 더 새로운 `yt-dlp`가 포함됩니다.

## Windows / Docker Desktop의 cookies.txt가 인식되지 않음

**증상** — `DOWNTIFY_COOKIES_FILE`을 설정했는데 Downtify가 쿠키가 없는 것처럼 동작합니다.

**원인** — 경로가 *컨테이너* 경로입니다. `C:\Users\me\cookies.txt` 같은 Windows 경로는 컨테이너 안에서 아무 의미가 없으며, 변수가 가리키려면 먼저 파일을 바인드 마운트해야 합니다.

**해결** — 변수를 아예 쓰지 말고 **설정** → **YouTube 쿠키**에서 파일을 업로드하세요. 이 방법은 마운트가 필요 없고 모든 플랫폼에서 똑같이 동작합니다.

변수를 계속 쓰고 싶다면 파일을 마운트하고, 호스트 경로가 아니라 마운트 대상을 가리키세요.

```yaml
volumes:
  - ./cookies.txt:/cookies.txt:ro
environment:
  - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

## 쿠키 업로드 버튼이 회색으로 비활성화됨

`DOWNTIFY_COOKIES_FILE`이 설정되어 있어 해당 배포가 자체 쿠키 파일을 관리하며, 웹 UI는 일부러 읽기 전용으로 유지됩니다. UI에서 쿠키를 관리하려면 변수를 제거하고 컨테이너를 다시 만드세요.

## 컨테이너를 업데이트한 뒤 업로드한 쿠키가 사라짐

업로드한 파일은 Downtify의 데이터 디렉터리(`/data`)에 있습니다. 이 디렉터리가 이름 있는 볼륨이나 바인드 마운트가 아니면, 컨테이너를 다시 만들 때 그 안의 모든 것(설정과 재생목록 모니터 데이터베이스 포함)이 사라집니다.

```yaml
volumes:
  - ./downloads:/downloads
  - downtify_data:/data   # ← 이것을 유지하세요
```

## 업로드할 때 "cookies.txt is invalid"

Downtify는 업로드할 때 파일을 검증합니다. **Netscape** 쿠키 저장소 형식이어야 합니다. 한 줄에 쿠키 하나, 필드는 탭으로 구분하고, 필요하면 `#` 주석을 둘 수 있습니다. JSON 내보내기, 스프레드시트, 복사한 `Cookie:` 헤더는 거부됩니다.

Netscape 형식으로 내보내는 브라우저 확장 프로그램을 사용하고([YouTube 쿠키](features/youtube-cookies.md) 참고), 탭이 `youtube.com`에 있을 때 내보내세요.

## 재생목록이 이미 있는 트랙을 다시 내려받음

Downtify는 자동으로 내려받은 모든 트랙을 데이터베이스에 기록하므로, 파일을 디스크의 다른 곳으로 옮겨도 다시 내려받지 않습니다. 트랙은 매시간 점검에서 파일이 다운로드 디렉터리에서 실제로 사라진 것을 확인한 뒤에만 다시 내려받습니다. [재생목록 모니터](features/playlist-monitor.md#how-it-works)를 참고하세요.

재시작할 때마다 파일이 사라진다면 `/downloads` 볼륨이 영구 저장되지 않는 것입니다. 위와 같은 해결책을 적용하세요.

## "Could not find a YouTube match for '…'"

YouTube Music도 일반 YouTube도 매처의 검사를 통과하는 결과를 돌려주지 못했습니다. 원본과 비슷한 제목, 하나 이상의 공통 아티스트, 노래방/커버/라이브/다른 언어 버전이 아닐 것, Spotify 길이와 30초 이내인 길이가 조건입니다. [작동 방식](how-it-works.md#fallback-to-standard-youtube)을 참고하세요.

보통 곡이 정말 YouTube에 없거나, 매우 다른 제목이나 아티스트 표기로만 올라와 있다는 뜻입니다. 올바른 영상을 직접 찾을 수 있다면 그 YouTube URL을 검색창에 붙여넣어 정확히 그 영상을 내려받으세요.

## 내려받은 오디오의 메타데이터나 커버가 잘못됨

Downtify는 Spotify에서 메타데이터를 가져오고 YouTube Music에서 오디오를 매칭합니다. 어긋남은 보통 매칭이 커버, 리믹스, 라이브 버전에 걸렸다는 뜻입니다. 검색 결과 대신 Spotify **앨범** 링크로 내려받으면 매처가 활용할 정보(트랙 번호, 앨범, 발매 유형)가 훨씬 많아집니다.

## 아직도 해결되지 않나요?

[github.com/henriquesebastiao/downtify/issues](https://github.com/henriquesebastiao/downtify/issues)에 다음을 담아 이슈를 열어 주세요.

- Downtify 버전(사이드바 하단과 **설정 → 정보**에 표시됨),
- 실패 시점 전후의 컨테이너 로그(`docker compose logs downtify`),
- 쿠키 설정 여부.
