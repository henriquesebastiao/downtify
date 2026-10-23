---
icon: lucide/share-2
---

# slskd ve Navidrome

Kendi sunucunuzda barındırılan kitaplıklar için iki isteğe bağlı entegrasyon:

- **[slskd](https://github.com/slskd/slskd)** — YouTube Music ve YouTube’un yanında ek bir ses kaynağı olarak, kendi slskd sunucunuz üzerinden Soulseek ağından parça indirin.
- **[Navidrome](https://www.navidrome.org/)** — indirdiğiniz çalma listelerini Navidrome’a yansıtın, böylece herhangi bir Subsonic istemcisinde görünsünler.

İkisi de varsayılan olarak kapalıdır ve **Ayarlar**’da yapılandırılır.

## Ses kaynakları ve yedek sırası

**Ayarlar → Ses kaynakları** sıralı bir listedir. Eklemek ya da kaldırmak için bir kaynağa dokunun; birden fazlası seçiliyse yeniden sıralamak için okları kullanın. Her parça kaynakları bu sırayla dener ve ses veren ilkinde durur:

| Kaynak | Ne yapar |
|--------|-------------|
| **YouTube Music** | Varsayılan. YouTube Music’te arar, kabul edilebilir eşleşme yoksa standart YouTube’a geçer — bkz. [Nasıl çalışır](../how-it-works.md#fallback-to-standard-youtube). |
| **YouTube** | Yalnızca standart YouTube’da arar. |
| **slskd** | slskd üzerinden Soulseek’te arar ve en iyi eşleşen dosyayı indirir. |

slskd’yi etkinleştirmek onu listenin başına koyar. slskd tek kaynak kalırsa YouTube Music ve YouTube yine de ondan sonra denenir; böylece slskd’nin bulamadığı bir parça yine iner. İndirme kuyruğu, her parçayı hangi kaynağın sunduğunu gösterir.

## slskd

### Kurulum

1. slskd’yi çalıştırın ve Downtify için bir API anahtarı oluşturun (slskd belgelerine bakın).
2. slskd’nin indirme klasörünü Downtify kapsayıcısına bağlayın — slskd’nin yazdığı aynı ana makine klasörü. Bkz. [Docker Compose → slskd ile](../getting-started/docker-compose.md#with-slskd-soulseek).
3. **Ayarlar → slskd (Soulseek)** içinde slskd’yi etkinleştirin ve şunları doldurun:
    - **slskd URL’si** — iki kapsayıcı bir Docker ağını paylaşıyorsa örn. `http://slskd:5030`.
    - **API anahtarı**.
    - **İndirme klasörü** — o klasörün bağlandığı yol, *Downtify kapsayıcısının içinde* (varsayılan `/slskd`), ana makine yolu değil.

slskd URL’siz veya API anahtarsız etkinleştirilirse kaydetme bir hata iletisiyle reddedilir.

### Bağlantıyı sınama

Kaydetmeden önce alanları denetlemek için alanların altındaki **Bağlantıyı sına**’ya basın — formda yazılanı, kaydedilmiş olsun olmasın kullanır ve hiçbir şeyi değiştirmez. Şunları bildirir:

| Sonuç | Ne anlama gelir |
|--------|---------------|
| **slskd 0.21.4’e bağlanıldı.** | Adres doğru ve API anahtarı kabul edildi |
| **slskd, Soulseek’te oturum açmış.** / **oturum açmamış** | slskd’nin kendisinin Soulseek ağında oturum açıp açmadığı. Açmamışsa arama açana kadar hiçbir şey bulmaz — bir uyarı, çünkü ayarların kendisi doğru |
| **Downtify `/slskd`’yi okuyabiliyor.** / **okuyamıyor** | Yukarıdaki indirme klasörünün *bu* kapsayıcıda var olup olmadığı ve okunabilir olup olmadığı. Bir uyarının olağan nedeni bağlanmamış bir klasördür — bkz. [Kurulum](#setup) |
| **slskd API anahtarını reddetti.** | Sunucu yanıtladı, ama bu anahtara değil |
| **… erişilemiyor / zamanında yanıt vermedi.** | Yanlış adres veya bağlantı noktası, sunucu kapalı ya da Downtify kapsayıcısından erişilemiyor |
| **slskd’ye benzemiyor.** | Bir şey yanıtladı ama slskd değil — çoğu zaman yanlış bir bağlantı noktası ya da adreste eksik bir temel yol |
| **HTTPS sertifikasına güvenilmiyor.** | Kendi ağınızda `http://` ya da güvenilir bir otoriteden sertifika kullanın; Downtify sertifika denetimlerini atlamaz |

Herhangi bir alanı düzenlemek son sonucu temizler, çünkü artık formdakini tanımlamaz. Düğme, adres ve anahtar doldurulana kadar devre dışı kalır.

### Bir parça nasıl eşleştirilir

Downtify slskd’de parçanın başlığı ve sanatçısıyla arar ve sonuçları dosya adı ve süresinin parçayla ne kadar uyuştuğuna göre sıralar. Eşit derecede iyi eşleşmeler arasında önce MP3’ü, sonra FLAC’i tercih eder ve 256 kbps’in altında bit hızı bildiren dosyaları atlar. Arka arkaya en fazla beş adayı dener. Bir aktarım bitince Downtify dosyayı tutmadan önce etiketlerini ve süresini parçayla karşılaştırır.

Kabul edilebilir bir şey çıkmazsa, aktarım **Toplam zaman aşımı** içinde bitmezse veya uzak eşte **Kuyruk zaman aşımı**’ndan uzun süre ilerlemeden kuyrukta beklerse, Downtify sonraki ses kaynağına geçer.

### Dosyaları yerinde bırak

**slskd dosyalarını yerinde bırak** açıkken (varsayılan) indirilen dosya slskd klasöründe kalır: Downtify üst verileri, kapağı ve sözleri doğrudan orada içine yazar ve kitaplıkta `slskd/…` yoluyla kaydeder. Kitaplık, oynatıcı ve M3U dosyaları bu yolu kullanır ve `/media/slskd/…` üzerinden sunulur.

Dosyayı bunun yerine dosya adı şablonunuza ve [dosya düzeni](file-organization.md) ayarlarınıza göre diğer indirmelerinizin yanına kopyalamak için kapatın.

::: info
slskd dosyaları özgün biçimlerini korur — Ayarlar’da seçilen biçime dönüştürülmezler.
:::

## Navidrome

### Kurulum

1. Navidrome’un müzik klasörünün Downtify’ın indirme klasörünü (ve slskd dosyalarını yerinde bırakıyorsanız slskd klasörünü) içerdiğinden emin olun. Navidrome bir çalma listesine ancak taradıktan sonra parça ekleyebilir.
2. **Ayarlar → Navidrome** içinde Navidrome’u etkinleştirin ve URL’sini, kullanıcı adını ve parolasını girin.
3. İsteğe bağlı olarak bir **yönetici** kullanıcı adı ve parolası ekleyin. Downtify böylece yeni parçaları eşleştirmeden önce Navidrome’un kendi zamanlanmış taramasını beklemek yerine Navidrome’dan kitaplığı taramasını ister.

### Bağlantıyı sınama

Kaydetmeden önce alanları denetlemek için alanların altındaki **Bağlantıyı sına**’ya basın — formda yazılanı, kaydedilmiş olsun olmasın kullanır ve hiçbir şeyi değiştirmez. Şunları bildirir:

| Sonuç | Ne anlama gelir |
|--------|---------------|
| **navidrome 0.53.3’e bağlanıldı.** | Adres doğru ve kullanıcı adı ile parola kabul edildi |
| **Bu hesap kitaplık taraması başlatabilir.** | Taramalar için kullanılan hesap bir yöneticidir. Doldurduğunuz yönetici kullanıcı adı ya da boş bıraktıysanız normal olandır |
| **Bu hesap kitaplık taraması başlatamaz.** | Navidrome yalnızca yöneticilerin tarama başlatmasına izin verir ve Downtify denediğinde bunu söylemez — yeni şarkılar yalnızca geç görünür. Bir yönetici kullanıcı adı ve parolası doldurun |
| **Yönetici hesabı yönetici değil.** | Girdiğiniz yönetici girişi çalışıyor ama normal bir kullanıcıya ait |
| **Navidrome yönetici kullanıcı adını veya parolasını reddetti.** | Tarama hesabının girişi yanlış; ana giriş ayrıca bildirilir |
| **Navidrome kullanıcı adını veya parolayı reddetti.** | Sunucu yanıtladı, ama bu girişe değil |
| **… erişilemiyor / zamanında yanıt vermedi.** | Yanlış adres veya bağlantı noktası, sunucu kapalı ya da Downtify kapsayıcısından erişilemiyor |
| **Navidrome’a benzemiyor.** | Bir şey yanıtladı ama Subsonic API değil — çoğu zaman yanlış bir bağlantı noktası ya da adreste eksik bir temel URL |
| **HTTPS sertifikasına güvenilmiyor.** | Kendi ağınızda `http://` ya da güvenilir bir otoriteden sertifika kullanın; Downtify sertifika denetimlerini atlamaz |

Tarama hakları yalnızca sorgulanır — sınama hiçbir zaman tarama başlatmaz. Herhangi bir alanı düzenlemek son sonucu temizler ve düğme adres, kullanıcı adı ve parola doldurulana kadar devre dışı kalır.

::: info Sayfaya hiçbir şey geri gönderilmez
Yanıt yalnızca bulunanı taşır — bir sürüm, bir yol, bir durum — asla parolanızı ya da Downtify’ın yaptığı isteği.
:::

### Çalma listesi eşitleme

Yansıtma yöneticiler tarafından yapılandırılır (Ayarlar → Navidrome); normal hesaplar yansı oluşturamaz, ama entegrasyon açıldığında indirmeleri başkalarınınki gibi yansıtılır.

**Navidrome’da çalma listesi oluştur** açıkken Downtify, şunlardan sonra aynı adda bir Navidrome çalma listesi oluşturur (veya günceller):

- bir Spotify çalma listesi indirmesi bittikten,
- bir [Çalma Listesi İzleyici](playlist-monitor.md) taraması parça ekledikten,
- parçalar Kitaplıktan silindikten ya da [kitaplık yolları düzeltildikten](library-catalog.md#fix-library-paths).

Parçalar Navidrome şarkılarıyla önce yola, sonra etiketlere göre eşleştirilir. **Navidrome çalma listelerini herkese açık yap**, çalma listesinin Navidrome’daki görünürlüğünü denetler.

::: warning Etiketleri çalma listesiyle uyuşmayan dosyalar silinir
Bir çalma listesi yenilendiğinde (silmelerden, **Kitaplık yollarını düzelt**’ten ya da zaten tam bir çalma listesinde **Eksikleri indir**’den sonra), bir Spotify parçası için kaydedilmiş bir kitaplık dosyası, gömülü başlığı/sanatçısı o parçayla açıkça uyuşmuyorsa **diskten silinir** — Downtify bunu yanlış bir indirme sayar. Etiketleri elle düzenliyorsanız bunu aklınızda tutun.
:::

### Çalma listesi kapağı

Kurulacak bir şey yok: [Çalma listesi kapağını kaydet](playlist-cover-art.md) açıkken Navidrome, Downtify’ın çalma listesinin M3U’sunun yanına yazdığı `.jpg`’yi, müzik klasörü o dosyayı kapsadığı sürece bir **yan görüntü (sidecar)** olarak — çalma listesi görsellerini çözmenin kendi yolu — alır. Downtify bunun için hiçbir API çağrısı yapmaz.

## Çalma listesi indirmeleri

**Kitaplık** sayfası, Downtify üzerinden indirdiğiniz Spotify çalma listelerini **Çalma listesi indirmeleri** altında listeler. Her çalma listesi için kitaplığınızda kaç parçanın, geçerli Spotify parça listesine kıyasla bulunduğunu görmek için genişletin. Buradan şunları yapabilirsiniz:

- **Eksikleri indir** — yalnızca henüz kitaplığınızda olmayan parçaları sıraya alır.
- Zaten indirilmiş parçaları **çal**.
- Eksik tek tek parçaları görmek ve indirmek için bir çalma listesini genişletin.
- Çalma listesini **sil** — aşağıya bakın.

### Bir çalma listesini silme

Bir çalma listesini silmek (bu panelden ya da Kitaplığın çalma listesi süzgecinin yanındaki **Çalma listesini sil** ile) ona kayıtlı her parçayı diskten kaldırır — **diğer çalma listelerinin de içerdiği parçalar dahil** — ayrıca M3U dosyasını ve yanına kaydedilen [kapağı](playlist-cover-art.md), ve onu izlemeyi bırakır. Bu parçaları paylaşan diğer çalma listelerinin M3U’su ve Navidrome çalma listesi arka planda yeniden yazılır.
