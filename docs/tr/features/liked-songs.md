---
icon: lucide/heart
---

# Beğenilen şarkılar

Bir şarkıyı beğenmek için kalbine dokunun. Bir şarkı beğenilir beğenilmez Downtify, beğendiğiniz tüm şarkıları içeren bir **Beğenilen şarkılar** çalma listesi tutar; böylece favorileriniz bir tık uzağınızda olur — Downtify’da ve kitaplığınıza bakan her medya sunucusunda.

Açılacak bir şey yok.

Kalpler dokunana aittir: birden çok hesabı olan bir sunucuda herkesin kendi beğenilen şarkıları vardır ([Kullanıcılar ve oturum açma](users.md#your-library) sayfasına bakın). Diskteki çalma listesi dosyası yöneticilerin kalplerini içerir; diğer herkesin beğenileri kitaplık veritabanında durur ve uygulamalarda aynı şekilde çalışır.


## Bir şarkıyı beğenme

Kalp, kitaplığınızdaki her şarkının yanında bulunur — indirmeler ve [mevcut müzik klasörlerinden](external-library.md) gelen parçalar:

- parça listelerinde — Kitaplık, albümler, sanatçılar ve çalma listeleri;
- [oynatıcı çubuğunda](player.md#player-bar) (640 piksel ve daha geniş ekranlarda);
- [Şimdi çalıyor](player.md#now-playing) içinde, şarkı başlığının yanında.

Beğenmek için dokunun, beğeniyi geri almak için tekrar dokunun. Yeşile dolar ve değişiklik hemen sunucuya yazılır; telefonunuzda dokunulan bir kalp masaüstünüzde de görünür — açık sekmeler ve cihazlar kendiliğinden takip eder.

Yalnızca kitaplığınızdaki şarkılar beğenilebilir. Henüz indirmediğiniz bir arama sonucunun kalbi yoktur; önce indirin.

## Çalma listesi

İlk beğeni çalma listesini oluşturur ve kısa bir bildirim onu açmayı önerir. Diğer çalma listeleri gibi listelenir — kenar çubuğunda, Ana sayfada ve **Kitaplık → Çalma listeleri** içinde —, ama her zaman **en başta**, kapak yerine bir kalple. Şarkıları en son beğenilen en üstte olacak şekilde sıralanır.

Son beğeni geri alınınca çalma listesi yine kaldırılır; ortada boş bir **Beğenilen şarkılar** kalmaz.

Başlık [dilinizi](internationalization.md) izler. Diskte çalma listesi, sabit adlı sade bir [M3U dosyasıdır](m3u-export.md):

```
<downloads>/Playlists/Downtify Liked Songs.m3u
```

Jellyfin, Navidrome, Plex ve benzerlerinin de onu göstermesinin nedeni budur: aynı dosyayı okurlar. Ad bilerek ayrılmıştır. Spotify’da *Liked Songs* adlı çalma listeleri yaygındır ve bu adla indirilen bir çalma listesi aksi halde aynı dosyaya yazardı.

## Tüm beğenileri kaldırma

Çalma listesini açın, ardından **⋯ → Tüm beğenileri kaldır**’a tıklayıp onaylayın. Tüm kalpler silinir ve çalma listesi kaybolur.

::: info Şarkılarınız kalır
Beğenileri kaldırmak hiçbir zaman ses dosyası silmez. Yalnızca kalpler ve çalma listesi kaldırılır — dosyalar kitaplığınızda durur. Bu, şarkılarını da silen indirilmiş bir çalma listesini silmekten farklıdır; **Beğenilen şarkılar** asla öyle ele alınmaz. Onu silmeyi istemek (uygulamada ya da [API](../api-reference.md#delete-apilibraryplaylist) üzerinden) yalnızca beğenileri temizler.
:::

## Beğenileri dosyalarla uyumlu tutma

Bir beğeni, verildiği dosyayı izler:

| Dosyaya olan | Beğeniye olan |
|--------------------------|--------------------------|
| Şarkıyı Downtify’da silersiniz | Beğeni onunla gider ve çalma listesi yeniden yazılır |
| Onu taşıyıp [Kitaplık yollarını düzelt](library-catalog.md#fix-library-paths)’i çalıştırırsınız | Beğeni dosyayı yeni yerine kadar izler |
| Downtify dışında kaybolur (çıkarılmış bir sürücü, elle silme) | Beğeni korunur, ama şarkı geri gelene kadar çalma listesinin dışında kalır |

Eksik bir dosyanın beğenisini korumak, çıkarılmış bir sürücünün kalplerinize mal olmaması demektir. Dosyaları elle sildiyseniz ve beğenilerin de gitmesini istiyorsanız **Tüm beğenileri kaldır**’ı kullanın ya da şarkıları silmeden önce beğenilerini geri alın.

## Bilmekte fayda var

- Beğeniler ses dosyalarında değil, kitaplık veritabanında (`downtify_library.db`, `/data` biriminizde) saklanır. Şarkının etiketlerine hiçbir şey yazılmaz.
- Çalma listesi Downtify tarafından [Navidrome](slskd-navidrome.md)’da oluşturulmaz. Sade bir M3U dosyasıdır; bir medya sunucusunun onunla ne yapacağı, o sunucunun M3U dosyalarını nasıl okuduğuna bağlıdır.
- [Çalma listesi dosyası](m3u-export.md), indirme ayarlarında *M3U çalma listeleri yaz* kapalıyken bile yazılır: özelliğin amacı çalma listesidir.

## API

`GET /api/likes`, `PUT /api/likes` ve `POST /api/likes/clear`; ayrıca [`GET /playlists`](../api-reference.md#get-playlists) üzerinde bir `liked` bayrağı. [API başvurusuna](../api-reference.md#likes) bakın.
