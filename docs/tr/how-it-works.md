---
icon: lucide/cog
---

# Nasıl çalışır

Downtify’ın indirme hattı üç aşamadan oluşur:

```
Spotify embed  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
  (metadata)         (audio match)          (download & tag)
```

## 1. Meta veri — Spotify gömme sayfasının okunması

Bir Spotify URL’si yapıştırdığınızda Downtify o parça, albüm veya çalma listesinin herkese açık `open.spotify.com/embed` sayfasını alır. Spotify hesabı, API anahtarı veya Premium abonelik gerekmez — gömme sayfası herkese açıktır.

**Parçalar** için gömme sayfası şunları döndürür: başlık, sanatçı(lar), albüm adı, yayın yılı, süre ve kapak resmi URL’si.

**Albümler ve çalma listeleri** için parça listesini döndürür. Çalma listesi gömmeleri yaklaşık 50–100 girişle sınırlıdır; bu yüzden Downtify, yüzlerce şarkılık çalma listelerini işlemek için tam listeyi Spotify’ın anonim `api.spotify.com` uç noktasından sayfalama ile de ister.

::: info Parça başına meta veri zenginleştirme
Çalma listesi gömme girişlerinde yayın yılı yoktur ve her parçanın kendi albüm kapağı yerine çalma listesi kapağı kullanılır. [Çalma Listesi İzleyici](features/playlist-monitor.md) için Downtify, indirmeden önce doğru kapağı ve yılı almak üzere her yeni parçayı tek tek yeniden alır.
:::

## 2. Ses eşleştirme — YouTube Music, sonra YouTube

Downtify, en iyi ses eşleşmesi için YouTube Music’i aramak üzere [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) kullanır. Arama sorgusu parça başlığı ve sanatçı adından oluşturulur.

Bir sonuç yalnızca başlığı kaynak başlığa benziyorsa ve en az bir sanatçıyı paylaşıyorsa kabul edilir. Spotify’ın tireli sürüm eki ile YouTube Music’in parantezli eki aynı sayılır (`Tubarões - Ao Vivo`, `Tubarões (Ao Vivo)` ile eşleşir) ve YouTube Music’in tek girişe sığdırdığı sanatçı kredisi (`A, B, and C`) karşılaştırmadan önce ayrılır. Sanatçı adlarının başındaki “The” yok sayılır (`Eden Project`, `The Eden Project` ile eşleşir) ve bir başlık, diğer parçalar farklı bir sürümü adlandırmadığı sürece yüklemenin başlığının ` - ` ile ayrılmış bir parçasıyla eşleşebilir (`くちづけDiamond - Kuchizuke Diamond`, `Game OST - Song Title - Artist`). Karaoke, cover, enstrümantal, hızlandırılmış/yavaşlatılmış, canlı (`Ao Vivo`/`En Vivo` dahil), akustik, remix ve başka dildeki sürümler (örn. `(Spanish Version)`), kaynak parçanın kendisi o sürüm değilse reddedilir. Kalan sonuçlar arasında süresi Spotify’ınkine en yakın olan kazanır; eşleşen albüm adı için bonus verilir. Hiçbir sonuç uygun değilse arama sözcükler diğer sırayla yinelenir (`<sanatçı> <başlık>` yerine `<başlık> <sanatçı>`) — YouTube Music sonuçları sözcük sırasına göre farklı sıralar ve bazı şarkılar yalnızca bir yönden üst sıralarda çıkar. Bu da bir şey bulamazsa ve albüm biliniyorsa albümün parça listesi doğrudan taranır.

### Standart YouTube’a geri dönüş

Bazı şarkılar YouTube Music’te yoktur ya da orada yalnızca farklı bir kayıt olarak bulunur. Bu yüzden standart YouTube da şu durumlarda aranır:

- YouTube Music’te **kabul edilebilir eşleşme yok**, ya da
- en iyi eşleşmenin süresi Spotify’ınkinden **10 saniyeden fazla** farklı — bu, farklı bir kayıt olduğunun güçlü bir işareti (örn. aynı başlıklı dublajlı bir sürüm).

Standart YouTube sonuçları aynı başlık, sanatçı ve sürüm denetimlerinden geçer ve Spotify’ın süresinden 30 saniyeden fazla sapanlar asla kabul edilmez. Bir YouTube sonucu, zayıf bir YouTube Music eşleşmesinin yerini yalnızca süresi kesin olarak daha yakınsa alır; aksi halde YouTube Music eşleşmesi korunur, çünkü katalog yüklemeleri genellikle en temiz sese sahiptir.

İki sitede de kabul edilebilir bir eşleşme yoksa parça, yanlış şarkıyı indirmek yerine `Could not find a YouTube match for '<title>'` ile başarısız olur.

Doğrudan girilen YouTube URL’leri için bu adım atlanır — Downtify o belirli videoyu indirir.

::: info Deezer bağlantıları
Yapıştırılan bir Deezer parça/albüm/çalma listesi/sanatçı bağlantısı (`deezer.com/track/…`) bir Spotify bağlantısı gibi çalışır: Deezer’ın herkese açık REST API’si başlığı, sanatçı(ları), albümü ve kapağı sağlar, her parça indirmeden önce YouTube’dan tam olarak akıtılabilir ve aynı adım onu YouTube Music/YouTube’da eşleştirir. Downtify’ın Deezer’ın API’sinin zaten döndürdüğünün ötesinde kendi Deezer diskografi çözümleyicisi yoktur; bu yüzden bir Deezer bağlantısı indirilir ve (çalma listesi için) kendi M3U’sunu ve kapağını alır, ancak [Çalma Listesi İzleyici](features/playlist-monitor.md) tarafından izlenemez.
:::

## 3. İndirme ve etiketleme — yt-dlp + ffmpeg + mutagen

### İndirme

[yt-dlp](https://github.com/yt-dlp/yt-dlp) sesi YouTube’dan indirir. Downtify onu, YouTube’un bot algılama zorluklarını aşmak için birkaç oynatıcı istemcisini sırayla (`ios`, `android`, `web_embedded`, `mweb`, `web`, `tv`) deneyecek şekilde yapılandırır. Gelişmiş anti-bot seçenekleri için [Ortam değişkenleri](getting-started/environment-variables.md) sayfasına bakın.

### Dönüştürme

[ffmpeg](https://ffmpeg.org/) ham sesi seçilen biçime (MP3, FLAC, M4A, OGG veya OPUS) seçilen bit hızında dönüştürür.

### Etiketleme

[mutagen](https://mutagen.readthedocs.io/) meta verileri dönüştürülen dosyaya yazar:

| Etiket | Yazılır |
|-----|---------|
| Başlık | Evet |
| Sanatçı(lar) | Evet |
| Albüm | Evet |
| Yıl | Evet |
| Albüm kapağı (JPEG) | Evet |
| Sözler (düz + eşzamanlı) | Evet, lrclib bir sonuç döndürürse |
| Müstehcen içerik işareti | Evet, şarkı açık içerikli olarak işaretliyse ([Müstehcen içerik işareti](features/explicit-marker.md) sayfasına bakın) |

Kullanılan tam ID3/Vorbis/MP4 etiketleri çıktı biçimine bağlıdır. Sözlerin nasıl gömüldüğüne dair ayrıntılar için [Şarkı sözleri](features/lyrics.md) sayfasına bakın.

## Gerçek zamanlı ilerleme

Downtify indirme ilerlemesini tarayıcıya bir **WebSocket** bağlantısı (`/api/ws`) üzerinden akıtır. yt-dlp ilerlemeyi bildirdikçe sunucu yüzde ve durum güncellemelerini tüm bağlı istemcilere yayınlar. Böylece ilerleme çubuğunun gerçek zamanlı hareket ettiğini görürsünüz — yoklama yok, sayfa yenileme yok.

## Dosya adlandırma ve düzen

Çıktı dosya adı, Ayarlar’da yapılandırılan şablondan oluşturulur (varsayılan: `{artists} - {title}`). Dosya adlarında geçersiz olan karakterler çıkarılır.

*Sanatçıya göre düzenle* açıkken dosya, ana sanatçının adını taşıyan bir alt klasöre konur. Aksi halde tekil parçalar indirme dizininin köküne, çalma listesi/albüm parçaları çalma listesi veya albüm başına bir alt klasöre gider.
