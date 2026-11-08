---
icon: lucide/shield-alert
---

# Müstehcen içerik işareti

Açık sözlü bir şarkı — çocuklara uygun olmayan bir dil — Spotify’daki gibi başlığının yanında küçük bir **E** taşır. Şarkıyla nerede karşılaşırsanız karşılaşın, indirmeden önce ve sonra görünür ve dosyayla birlikte kalır.

## Nerede görürsünüz

- **Arama sonuçları, yapıştırılan bağlantılar, Müzik listeleri ve Bulucu** — hizmetin açık içerikli dediği her şarkıda. İndirmeden önce anlarsınız.
- **Kitaplık** — Parçalar sekmesinde, albüm, sanatçı ve çalma listesi sayfalarında ve “şarkı ekle” seçicisinde.
- **Oynatıcı** — oynatıcı çubuğunda başlığın yanında, **Şimdi çalıyor** ve **Sıradaki** içinde.

“Açık içerik” yazısını görmek için **E**’nin üzerine gelin (ya da bir ekran okuyucunun okumasına izin verin).

## İşaret nereden gelir

İndirdiğiniz hizmet karar verir: Spotify, YouTube Music ve Deezer açık içerikli şarkılarını ayrı ayrı işaretler ve Downtify seçtiğinizin söylediğini kullanır. Downtify bir şarkıyı YouTube Music’ten indirdiğinde işaret, **gerçekte indirdiği videoyu** tanımlar: şarkı Spotify’da açık içerikliyse ama Downtify temiz bir versiyonla eşleştiyse dosya işaretlenmez; Spotify temiz diyorsa ama eşleşme açık içerikliyse işaretlenir.

Hizmetin işaretlemediği bir şarkı hiç işaret almaz — bu temiz olduğunun onaylanması demek değildir ve Downtify hiçbir zaman “temiz” işareti yazmaz.

## Dosyada

İşaret, iTunes’un yaptığı gibi dosyanın etiketlerine yazılır; böylece onu anlayan medya sunucuları ve oynatıcılar da kullanabilir. Navidrome tam olarak bu etiketleri bir parçanın açık içerik durumu olarak okur.

| Biçim | Etiket |
|--------|-----|
| MP3 | `ITUNESADVISORY` metin çerçevesi (`TXXX`), değer `1` |
| FLAC, OGG, OPUS | `ITUNESADVISORY` yorumu, değer `1` |
| M4A | `rtng` atomu, değer `1` |

Önceden sahip olduğunuz dosyalar da aynı şekilde okunur: iTunes, MusicBrainz Picard veya başka bir etiketleyicinin `1` (ya da eski `4`) ile işaretlediği her şey de **E**’yi gösterir; [ek klasörlerdeki](external-library.md) şarkılar dahil.

::: info Bu sürümden önce indirilen şarkılar
Downtify’ın işaret var olmadan önce yazdığı dosyaların etiketlerinde hiçbir şey yoktur, bu yüzden şarkı açık içerikli olsa bile **E** göstermezler. İşaretlemek için şarkıyı [Sesi değiştir](replace-audio.md) ile ya da baştan yeniden indirin. Bir dosya, [Kitaplığı iyileştir](library-upgrade.md) veya Sesi değiştir onu yeniden yazdığında işaretini korur: işaret yalnızca eklenir, hiç silinmez.
:::

Güncellemeden sonra Kitaplık ilk kez yüklendiğinde Downtify, kodek ve türü göstermeyi öğrendiği zamanki gibi, işareti aramak için her dosyanın etiketlerini yeniden okur. Yavaş bir diskteki büyük bir kitaplıkta bu bir kez, kısa bir süre alır.

## Uygulama geliştiricileri için

[Mobil istemci sözleşmesi](../mobile-client-contract.md) ve [API başvurusu](../api-reference.md#get-tracks) `explicit` alanını anlatır: açık içerikli parçalarda `true`, diğerlerinde yok.
