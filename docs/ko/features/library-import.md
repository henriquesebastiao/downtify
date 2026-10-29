---
icon: lucide/import
---

# 라이브러리 가져오기(CSV)

다른 서비스에서 라이브러리를 이미 내보냈나요? 노래를 하나씩 추가하는 대신 CSV를 가져와 모든 트랙을 한 번에 다운로드 대기열에 넣으세요.

## 지원하는 내보내기 도구

| 도구 | 비고 |
|------|-------|
| [Soundiiz](https://soundiiz.com/) | |
| [TuneMyMusic](https://www.tunemymusic.com/) | |
| [Exportify](https://github.com/watsonbox/exportify) | |

Downtify는 특정 도구의 정확한 열 구조를 고정해 두지 않습니다. 대신 CSV의 머리글 행을 대소문자 구분 없이 알려진 별칭 집합(`Title` / `Track` / `Track Title` / `Track Name` / `Song` / …, `Artist` / `Artists` / `Artist Name` / `Artist Name(s)` / …, `Album` / `Album Name` / `Album Title` / …)과 비교하므로, 세 도구 중 어느 것의 내보내기 파일이든, 같은 열 이름을 쓴 직접 만든 CSV든 이름을 바꾸지 않고도 동작합니다.

제목과 아티스트는 필수입니다. 앨범은 있으면 읽어서 트랙의 앨범 이름(대기열, 매칭, 파일 태그)으로 저장합니다. 일부 도구가 포함하는 다른 열(ISRC, Spotify 트랙 URI, 길이)은 무시합니다. 각 행은 자유 입력 검색과 같은 방식으로 YouTube Music을 통해 해석됩니다.

## 가져오는 방법

1. 홈 페이지의 검색창 아래에서 **CSV 가져오기 (Soundiiz, Exportify…)**를 클릭합니다.
2. 내보낸 `.csv` 파일을 고릅니다.

파일은 전부 브라우저에서 읽은 뒤 일반 텍스트로 서버에 전송되며, 다른 곳에는 업로드되지 않습니다. Downtify가 파일을 분석해 인식된 모든 행을 대기열에 넣고, 다른 일괄 다운로드와 똑같이 WebSocket으로 진행 상황이 전해지는 다운로드 대기열로 이동합니다.

가져온 묶음은 파일 이름(`.csv`를 뺀 이름)을 따르며, 다른 재생목록 다운로드와 마찬가지로 해당 설정이 켜져 있으면 [M3U 파일](m3u-export.md)이 만들어집니다.

## 제한과 오류 처리

- 파일당 최대 **2,000행**입니다. 더 큰 내보내기는 여러 파일로 나누세요.
- 제목이나 아티스트가 없는 행은 조용히 건너뜁니다. 앨범 열이 없거나 앨범 칸이 비어 있어도 괜찮습니다. YouTube Music이 나중에 앨범을 채울 수 있습니다.
- 한 칸에 아티스트가 여러 명인 경우(`,` 또는 `;`로 구분)에는 목록으로 나눕니다.
- 머리글에 인식 가능한 제목/아티스트 열이 없으면, 찾은 열 이름을 알려 주는 오류와 함께 가져오기 전체가 처음부터 거부되며, 아무것도 대기열에 들어가지 않습니다.

## 요청 제한 피하기

큰 라이브러리를 가져오면 짧은 시간에 YouTube Music 검색과 다운로드가 많이 대기열에 들어가므로 요청 제한에 걸리기 쉽습니다. 큰 파일을 가져오기 전에 설정에서 **[동시 다운로드 수](download-settings.md#parallel-downloads)**를 낮추고 **[다운로드 간격](download-settings.md#delay-between-downloads)**을 켜는 것을 고려해 보세요.

## API

기반이 되는 엔드포인트는 API 레퍼런스의 [`POST /api/download/csv`](../api-reference.md#post-apidownloadcsv)를 참고하세요.
