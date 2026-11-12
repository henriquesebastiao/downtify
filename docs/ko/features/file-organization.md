---
icon: lucide/file-headphone
---

# 파일 정리

새 서버는 파일을 아티스트와 앨범별로 정리합니다(`아티스트/앨범/…`). **아티스트별로 정리**와 **앨범별로 정리**가 기본으로 모두 켜져 있습니다. 아래의 평면 구조를 쓰려면 둘 다 끄세요. 이 기본값이 생기기 전에 설정한 서버는 기존 선택을 유지합니다.

## 평면 구조(둘 다 끔)

개별 트랙과 YouTube 검색 결과는 다운로드 폴더의 최상위에 바로 저장됩니다. 재생목록과 앨범의 트랙은 재생목록 또는 앨범별 하위 폴더에 저장됩니다.

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← 개별 트랙
```

## 아티스트별로 정리

**설정 → 다운로드 및 파일 → 아티스트별로 정리**를 켜면(기본값) 재생목록과 앨범 다운로드를 포함한 모든 트랙이 앨범 아티스트 이름의 하위 폴더로 묶입니다([여러 아티스트와 컴필레이션](#several-artists-and-compilations) 참고).

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

이 구조는 `아티스트/곡.ext` 폴더 구성을 기대하는 미디어 서버(Jellyfin, Navidrome, Plex)와 라이브러리 관리 도구(Beets)와 호환됩니다.

## 여러 아티스트와 컴필레이션

곡 하나에 여러 아티스트가 참여하는 경우가 많습니다. Downtify는 이들을 모두 파일의 **아티스트** 태그에 남기고, 각 아티스트를 **ARTISTS** 태그(MP3에서는 `TXXX:ARTISTS`)에도 따로 기록합니다. 그래서 플레이어가 `Earth, Wind & Fire` 같은 이름을 쉼표에서 나눌 일이 없습니다. 하지만 폴더는 한 아티스트의 것입니다. 바로 **앨범 아티스트**, 컴필레이션이라면 그 트랙의 첫 번째 아티스트입니다.

- 앨범 아티스트는 원본(Spotify, YouTube Music 또는 Deezer)이 **앨범**에 표시한 아티스트로, 앨범의 모든 트랙에서 같으며 **앨범 아티스트** 태그에 기록됩니다. 원본에 표시가 없으면 트랙의 첫 번째 아티스트입니다.
- 듀오나 그룹은 한 아티스트입니다. YouTube Music은 일부 팀을 멤버 단위로 한 항목에 한 명씩 표시합니다(`Henrique & Juliano`가 앨범과 각 트랙에서 `Henrique`와 `Juliano`로 오고, 때로는 `Jorge & Mateus`가 `Mateus`와 `Jorge`처럼 순서가 바뀌기도 합니다). 표시된 이름마다 YouTube Music 채널로 연결되는데, 한 멤버의 링크가 옆에 표시된 이름들로 이루어진 팀 전체 이름의 채널로 이어지면 Downtify는 그 이름들을 다시 팀 이름으로 합칩니다. 폴더와 **앨범 아티스트**, **아티스트**, **ARTISTS** 태그가 모두 `Henrique & Juliano`가 됩니다. 실제 협업(각 아티스트가 자기 채널로 연결)은 모든 아티스트를 그대로 둡니다. YouTube Music이 어느 멤버도 팀 채널에 연결하지 않으면 이름은 나뉜 채로 남지만, 라이브러리는 항상 다른 사람 옆에만 표시되는 이름에는 페이지를 만들지 않습니다([라이브러리 카탈로그](library-catalog.md#library-page) 참고).
- 게스트는 이를 바꾸지 않습니다. Michael Jackson의 *Thriller*에 게스트가 참여한 *The Girl Is Mine*은 `Michael Jackson/Thriller/`에 남고, 싱글 *Lady Marmalade*(Christina Aguilera, Lil' Kim, Mýa, P!nk)는 `Christina Aguilera/`로 갑니다.
- 원본 스스로 **Various Artists**로 표시한 앨범(사운드트랙, "Now That's What I Call…" 등)만 컴필레이션입니다. 직접 [표시](#marking-an-album-as-various-artists)한 경우는 예외입니다. YouTube Music의 개별 곡은 컴필레이션이 되지 않습니다. YouTube Music은 같은 오디오를 여러 발매반에 올려 두고 그중 아무것이나, 흔히 컴필레이션을 앨범으로 보여 주기 때문에 YouTube Music 앨범 전체를 내려받을 때만 해당합니다. 그 트랙들은 앨범 아티스트로 "Various Artists"와 컴필레이션 플래그(MP3는 `TCMP`, FLAC/Ogg/Opus는 `COMPILATION`, M4A는 `cpil`)를 받습니다. 그래야 폴더가 아니라 이 태그로 앨범을 묶는 Navidrome 등의 미디어 서버에서 앨범이 하나로 유지됩니다. 다만 디스크에서는 **아티스트별로 정리**가 `Various Artists` 폴더를 만들지 않습니다. 각 트랙은 자기 첫 번째 아티스트의 폴더로 갑니다.
- 예전 버전의 Downtify는 여러 아티스트가 참여한 곡에 컴필레이션 플래그 없이 **Various Artists**를 기록했습니다. 라이브러리는 그런 곡을 예전처럼 첫 번째 아티스트의 앨범에 계속 보여 주며, **Various Artists로 표시**를 누르면 앨범이 진짜 컴필레이션이 됩니다.

```
downloads/
├── Christina Aguilera/
│   ├── Lady Marmalade/
│   │   └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
│   └── Moulin Rouge/                  ← 사운드트랙(컴필레이션)에서
│       └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
└── David Bowie/
    └── Moulin Rouge/                  ← 같은 사운드트랙
        └── David Bowie - Nature Boy.mp3
```

싱글의 *Lady Marmalade*와 *Moulin Rouge* 사운드트랙의 *Lady Marmalade*는 서로 다른 두 발매반이며, 각각 자기 앨범과 함께 정리됩니다. 사운드트랙의 트랙들은 각 아티스트의 폴더에 흩어지지만 하나의 "Various Artists" 컴필레이션으로 태그되므로, 라이브러리와 미디어 서버에서는 *Moulin Rouge*가 여전히 한 앨범으로 보입니다.

### 앨범을 Various Artists로 표시하기

원본이 여러 아티스트에게 똑같이 속한 발매반을 한 아티스트에게만 돌릴 때가 있습니다. Deezer는 싱글 *Lady Marmalade*를 Christina Aguilera 아래에만 둡니다. 관리자는 라이브러리의 앨범 페이지에서 **대기열에 추가** 옆의 **Various Artists로 표시** 버튼으로 이를 바로잡을 수 있습니다.

- 앨범의 모든 트랙이 앨범 아티스트로 "Various Artists"와 컴필레이션 플래그를 받습니다. 파일의 다른 부분은 바뀌지 않으며 파일도 제자리에 있습니다(컴필레이션의 트랙은 원래 자기 첫 번째 아티스트 폴더에 있습니다). 각 파일은 작업용 사본을 거쳐 다시 쓰이고, 수정 날짜를 유지하며, 다시 쓰기에 실패하면 그대로 남습니다.
- 라이브러리에서는 앨범이 **앨범** 탭에 **Various Artists**의 앨범으로 표시되고(각 트랙은 자기 아티스트 페이지에 남습니다), 앨범 페이지도 그쪽으로 따라갑니다.
- Downtify는 이 앨범을 기억합니다. 나중에 내려받는 이 앨범의 트랙도 같은 태그를 받습니다.
- 컴필레이션에서는 같은 버튼이 **Various Artists 표시 해제**로 바뀝니다. 표시를 되돌리고 앨범이 원래 갖고 있던 앨범 아티스트를 복원합니다. 원본이 컴필레이션으로 만든 앨범에서도 동작하며, 이때는 대부분의 트랙이 처음에 적은 아티스트가 앨범 아티스트가 되고, 이후 이 앨범을 다시 내려받아도 표시되지 않습니다.

버튼은 관리자에게만 보입니다. 미디어 서버는 다음 라이브러리 스캔 때 변경을 반영합니다.

## M3U와 아티스트 폴더

*아티스트별로 정리*가 켜져 있고 M3U 생성도 켠 상태로 Spotify 재생목록을 다운로드하면, M3U는 재생목록 하위 폴더 안이 아니라 `<downloads>/Playlists/<재생목록-이름>.m3u`에 놓입니다. 트랙이 이제 여러 아티스트 폴더에 흩어져 있기 때문입니다. M3U 안의 상대 경로는 라이브러리를 어디에 마운트하든 올바르게 해석됩니다.

## 설정 변경

설정은 모든 **새** 다운로드에 즉시 적용됩니다. 이미 디스크에 있는 파일은 이동하지 않습니다.

## 트랙을 삭제하면 빈 폴더도 정리됩니다

라이브러리 페이지에서 트랙을 삭제하면 재생목록, 아티스트 또는 앨범 폴더가 비는 즉시 함께 삭제되고, 비게 된 상위 폴더도 계속 거슬러 올라가며 정리합니다(예: 마지막 앨범이 사라진 뒤의 아티스트 폴더). 삭제되지 않는 다운로드 디렉터리 자체에서 멈춥니다. 다른 트랙, `.m3u`, 아직 사용 중인 `cover.jpg` 등 다른 것이 남아 있는 폴더는 그대로 둡니다.

## 여러 트랙을 한 번에 선택하고 삭제

라이브러리의 트랙 목록에는 모든 트랙에 체크박스가 있고, 현재 필터와 일치하는 모든 트랙을 선택하는 **전체 선택** 체크박스도 있습니다([라이브러리 페이지](library-catalog.md#library-page) 참고). 선택 바의 **라이브러리에서 삭제**는 한 번의 요청(`DELETE /delete/batch`, [API 레퍼런스](../api-reference.md) 참고)으로 모두 삭제하며, 트랙을 하나씩 삭제할 때와 같은 트랙별 정리(`.lrc`, 고아가 된 `cover.jpg`, 빈 폴더)를 합니다.

앨범이나 재생목록 전체를 삭제하려면 열어서 **⋯** 메뉴의 **삭제**를 고르세요. 한 아티스트의 모든 곡은 트랙 목록의 필터에 아티스트 이름을 입력한 뒤 **전체 선택**을 하고 삭제하면 됩니다.
