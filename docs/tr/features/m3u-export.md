---
icon: lucide/list-music
---

# M3U dışa aktarma

Downtify, bir Spotify çalma listesi indirildiğinde — elle ya da [Çalma Listesi İzleyici](playlist-monitor.md) ile — standart bir `EXTM3U` çalma listesi dosyasını otomatik olarak üretir.

## Dosya konumu

| Durum | M3U yolu |
|-----------|---------|
| Çalma listesi normal indirildi | `<downloads>/<çalma-listesi-adı>/<çalma-listesi-adı>.m3u` |
| Çalma listesi *Sanatçıya göre düzenle* açıkken indirildi | `<downloads>/Playlists/<çalma-listesi-adı>.m3u` |

*Sanatçıya göre düzenle* açıkken parçalar birden çok sanatçı klasörüne dağılır; bu yüzden M3U, çalma listesi alt klasörü yerine merkezi bir `Playlists/` dizinine konur.

[Beğenilen şarkılar](liked-songs.md) da düzen ne olursa olsun ve *M3U çalma listeleri yaz* açık olsun olmasın `Playlists/Downtify Liked Songs.m3u` dosyasına yazılır.

## Göreli yollar

M3U içindeki parça yolları mutlak yollar olarak değil, **M3U dosyasının kendisine göre göreli** yazılır. Bu, aynı dosyanın hem Downtify kapsayıcısı içinden (`/downloads/…`) hem de aynı kitaplığı farklı bir kökte bağlayan başka bir tüketiciden — örneğin `/nas/music/…` altındaki Jellyfin — okunsa da çalışması demektir. Medya sunucunuzu aynı kitaplık bağlantı noktasına yöneltmeniz yeter; çalma listesi tek bir bütün olarak görünür.

## Açma / kapatma

M3U üretimi **Ayarlar → İndirmeler ve dosyalar → M3U çalma listeleri yaz** ile denetlenir (varsayılan olarak açık). Kapatmak M3U oluşturmayı tamamen atlar; indirme akışının geri kalanı değişmez.

## Kapak resmi

Bu ayarın hemen altındaki **Çalma listesi kapağını kaydet** (varsayılan olarak açık), çalma listesinin kendi kapak resmini M3U’sunun yanına aynı adla yazar — parçalardan önce, böylece klasör en baştan çalma listesi gibi görünür. Downtify de çalma listesi için parça kapaklarından oluşan bir ızgara yerine bu resmi gösterir. Kitaplıkta oluşturduğunuz bir çalma listesi, aynı şekilde yazılan en fazla dört parça kapağından oluşan bir mozaik alır. [Çalma listesi kapakları](playlist-cover-art.md) sayfasına bakın.

## Ne zaman yazılır

M3U, **her parçanın indirmesi bittikten sonra** yeniden yazılır; böylece çalma listesi dosyası sonda bir anda belirmek yerine indirme ilerledikçe büyür. Bu, çalma listesi ve albüm indirmeleri, [CSV içe aktarmaları](library-import.md) ve [Çalma Listesi İzleyici](playlist-monitor.md#m3u-integration) taramaları için aynı şekilde geçerlidir.

Bu, ilk parça düştüğü andan itibaren çalma listesinin çalınabilir olduğu, eşitlemenin ilerledikçe çalıştığını görebildiğiniz ve tek bir yavaş ya da takılmış indirmenin M3U’nun — veya bitmiş parçaların — görünmesini asla engelleyemeyeceği anlamına gelir.

Tüm çalıştırma bittiğinde son bir yeniden yazma yapılır. Her parçayı (bu çalıştırmanın indirdiklerinin bellekteki listesi yerine) dosya sistemine karşı çözümler; böylece önceki çalıştırmalardan kalan dosyaları da toplar ve çalıştırma sırasında diskte değişen her şeyi düzeltir.

Her yazma, parçaları indirmelerin bitiş sırasına göre değil **çalma listesi sırasına** göre listeler; bu yüzden kısmen yazılmış bir M3U bile doğru sıradadır.

::: info Zaten diskte olan parçalar
Önceki bir çalıştırmada indirilen parçalar M3U’da baştan sona kalır — yalnızca son yazmayla eklenmezler, ilk yazmadan itibaren dahildirler.
:::

## Yeniden üretim

M3U her çalıştırmada baştan üretilir — aynı çalma listesi adresini yeniden yapıştırmak, önceki çalıştırmalarda eksik olan parçalar dahil eksiksiz ve sıralı bir dosya üretir.

İndirilemeyen veya YouTube Music’te eşleşmesi olmayan parçalar sessizce atlanır.

## Uyumluluk

Üretilen dosya şunları kullanır:

- BOM’suz UTF-8 kodlaması
- LF satır sonları
- Standart `#EXTM3U` / `#EXTINF` biçimi

Jellyfin, Navidrome, Plex, VLC, Kodi, Sonos ve standart M3U çalma listelerini okuyan diğer tüm oynatıcı ve medya sunucularıyla uyumludur.

## Kendi oluşturduğunuz çalma listeleri

**Kitaplık → Çalma listeleri → Yeni çalma listesi**, `Playlists/` altına aynı türde bir M3U yazar; Downtify’ın onu indirilmiş bir Spotify/YouTube çalma listesinden ayırt edebilmesi için fazladan bir `#EXTDOWNTIFY:manual` satırı eklenir. Yeniden adlandırabilir, şarkı ekleyip çıkarabilirsiniz ([ek klasörlerdeki](external-library.md) şarkılar dahil). Bu çalma listesini silmek, bir parçayı silmek veya bir ek klasörün eşlemesini kaldırmak M3U’yu günceller; ses yalnızca parçanın kendisini ya da içe aktarılmış bir çalma listesini sildiğinizde silinir.

### Bir çalma listesine şarkı ekleme

Yöneticiler şarkıları bu çalma listelerinden birine ya da yeni birine birkaç yerden ekleyebilir:

- **Bir şarkının ⋯ menüsü** (herhangi bir parça listesinde) → **Çalma listesine ekle**.
- Kitaplıkta **birkaç şarkı seçin** ve **Çalma listesine ekle**’ye basın.
- **Bir albümün ⋯ menüsü** → **Çalma listesine ekle**, albümün tüm şarkılarını ekler.
- **Bir sanatçının ⋯ menüsü** (sanatçının sayfasında) → **Çalma listesine ekle**, sanatçının kitaplığınızdaki her şeyi albüm albüm ekler.

Her menü çalma listelerinizi ve bu şarkılarla birlikte yeni bir liste oluşturan **Yeni çalma listesi…** girişini listeler. Çalma listesinde zaten bulunan şarkı atlanır ve onay, gerçekte kaç tanesinin eklendiğini (ya da hepsinin zaten orada olduğunu) söyler. Bir çalma listesi en fazla 500 şarkı alır.
