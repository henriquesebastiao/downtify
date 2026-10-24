---
icon: lucide/smartphone
---

# Mobil uygulamalar

Downtify telefonunuzdaki uygulamalara hizmet verebilir: kitaplığa göz atar ve doğrudan sunucunuzdan akıtırlar, çevrimdışı dinlemek için şarkıları telefonda tutarlar. Bir uygulamanın ihtiyaç duyduğu her şey **Ayarlar → Uygulamalar** içinde kurulur: telefonları eşleştirme ve sunucunun adı. Sunucuyu kimlerin kullanabileceği ise [Kullanıcılar ve oturum açma](users.md) sayfasındaki hesaplarla belirlenir.

::: warning Uygulama hâlâ geliştirme aşamasında
**Ayarlar → Uygulamalar** *Deneysel* olarak işaretlidir. Bu sayfada anlatılan sunucu tarafı bitmiştir ve çalışır, ama **Android uygulamasının hiçbir sürümü henüz yayımlanmadı**; bu yüzden şimdilik kurulacak bir şey yok ve eşleştirme ile akışın ayrıntıları Downtify sürümleri arasında hâlâ değişebilir.

Uygulama [henriquesebastiao/downtify-android](https://github.com/henriquesebastiao/downtify-android) adresinde açık biçimde geliştirilir. Başka her şey aynı API üzerine kurulabilir — bkz. [mobil istemci sözleşmesi](../mobile-client-contract.md).
:::

## Bir telefonu eşleştirme

1. **Ayarlar → Uygulamalar**’ı açın ve **Telefon eşleştir**’e basın.
2. Uygulamada **Kodu tara**’yı seçin ve kamerayı QR koda doğrultun — veya altında gösterilen 8 karakterlik kodu yazın (`K7QM-2XPD`; harf büyüklüğü ve tireler önemli değil).
3. Telefon eşleşince pencere bunu onaylar ve telefon **Eşleştirilmiş uygulamalar** altında görünür.

Telefon **hesabınızla** eşleştirilir: sizin olarak çalar ve etkinliğinizde görünür. Hesabı olan herkes kendi telefonlarını eşleştirebilir.

Bir kod **bir kez**, **beş dakika** boyunca çalışır ve yanlış kod denemeleri hız sınırlıdır. Telefon kendine ait bir anahtar alır ve onu saklar; sunucu yalnızca onun bir hash’ini depolar.

**Eşleştirilmiş uygulamalar** telefonlarınızı (yönetici herkesinkini, her birinin sahibiyle birlikte görür) platformu, en son ne zaman ve hangi adresten görüldüğüyle listeler. **Eşleştirmeyi kaldır** bir telefonu hemen durdurur — sonraki isteği başarısız olur, açık bir bağlantı kapatılır ve paylaştığı bağlantılar ([Yayın (cast)](#casting) bölümüne bakın) çalışmayı bırakır. Yeniden kullanmak için tekrar eşleştirin.

## Eşleştirilmiş bir uygulama neler yapabilir

Eşleştirilmiş uygulamalar göz atabilir, çalabilir, beğenebilir, şarkıları çevrimdışı tutabilir ve sunucudan müzik indirmesini isteyebilir — ama ayarları, kimlik bilgilerini değiştiremez ya da dosya silemez; bunun için yönetici olarak oturum açılmış web sayfası gerekir.

**Ayarlar → Uygulamalar → Her yerden çıkış yap**, tüm uygulamalarınızın eşleştirmesini kaldırır ve bunun da dahil olduğu her tarayıcıdan oturumunuzu kapatır. Oturum açma, hesaplar ve unutulan parola [Kullanıcılar ve oturum açma](users.md) sayfasında.

## Sunucuyu ağınızda bulma

Sunucu yerel ağda kendini duyurur (mDNS / Bonjour, `_downtify._tcp` olarak); böylece bir uygulama onu hiçbir şey yazmadan **Bu ağda bulundu** altında — ad, adres ve sürüm — listeler. Ad, **Ayarlar → Uygulamalar → Sunucu adı** altında belirlenendir (siz değiştirene kadar makinenin ana makine adı).

::: info Docker’ın varsayılan ağı duyuruyu gizler
Docker’ın varsayılan *bridge* ağında duyuru Docker’ın içinde kalır ve telefonlar onu görmez. Kapsayıcıyı `network_mode: host` ile çalıştırın ([Docker Compose](../getting-started/docker-compose.md#finding-the-server-from-the-apps) sayfasına bakın) ya da sunucunun adresini uygulamaya yazın — gerisi aynı çalışır.
:::

Duyuruyu durdurmak için `DOWNTIFY_DISCOVERY=false` ayarlayın.

## Akış kalitesi

Uygulamalar dosyaları olduğu gibi çalar (**Orijinal**) ya da sunucudan daha küçük bir kopya ister: 96–320 kbps’te Opus, AAC veya MP3 — mobil veride kullanışlı. Sunucu bu kopyayı bir şarkı ilk kez bu şekilde çalındığında ffmpeg ile yapar (tipik bir şarkı için birkaç saniye) ve saklar; böylece ileri-geri sarma her dosyadaki gibi çalışır ve sonraki çalma anlıktır.

- Zaten yeterince küçük olan bir dosya (istenen bit hızında veya altında kayıplı bir dosya) olduğu gibi akıtılır, asla yeniden kodlanmaz.
- Kopyalar `/data/transcode_cache` içinde tutulur, varsayılan olarak en fazla 2 GB; en uzun süredir çalınmayanlar önce gider. Aynı anda en fazla iki tane yapılır. İki sınır da [ortam değişkenleridir](../getting-started/environment-variables.md#mobile-apps-and-sign-in).
- Bir kopya yapılırken telefon vazgeçerse sunucu onu yapmayı bırakır.

## Yayın (cast)

Uygulamalar bir şarkıyı bir Chromecast’e veya sesi kendi başına çeken başka bir oynatıcıya gönderebilir. Uygulama sunucudan, o tek şarkı için sınırlı bir süre (varsayılan bir saat) ve yalnızca telefon eşleşmiş kaldığı sürece çalışan bir bağlantı alır; telefonun hiçbir anahtarı içine girmez.

## Ters proxy arkasında

Downtify nginx, Caddy, Traefik veya benzerinin arkasındaysa (HTTPS için ya da dışarıdan erişmek için):

- **WebSocket’i geçirin.** `/api/ws` için `Upgrade`/`Connection` başlıklarının iletilmesi gerekir (Caddy ve Traefik bunu varsayılan olarak yapar; nginx için `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";` gerekir).
- **Range isteklerini** değiştirmeden geçirin ve ses yanıtlarını arabelleğe almayın (nginx: `/api/v1/` ve `/downloads/` için `proxy_buffering off;`), yoksa sarma ve büyük dosyalar zarar görür.
- **Downtify’a hangi proxy’ye güveneceğini söyleyin.** `DOWNTIFY_TRUSTED_PROXIES` değerini proxy’nin adresine ayarlayın (örn. `172.18.0.0/16`). Downtify ancak o zaman istemcinin adresi (hız sınırları, Eşleştirilmiş uygulamalar’daki “son görülme”) için `X-Forwarded-For`’u, oturum çerezini güvenli işaretlemek ve isteklerin nereden geldiğini denetlemek için `X-Forwarded-Proto`/`X-Forwarded-Host`’u kullanır. Bunlar olmadan o başlıklar yok sayılır — herkes gönderebilir.
- Sunucuya dışarıdan erişilebiliyorsa **HTTPS kullanın**: parola ve uygulamaların anahtarları her istekle birlikte yol alır.

## Uygulama geliştiricileri için

Bir uygulamanın izlediği tüm akış — keşif, eşleştirme, kitaplığı eşitleme, akış, çalmaları bildirme — [mobil istemci sözleşmesinde](../mobile-client-contract.md), her uç nokta ise [API başvurusunda](../api-reference.md#server-and-sign-in) yer alır.
