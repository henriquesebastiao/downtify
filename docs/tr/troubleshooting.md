---
icon: lucide/life-buoy
---

# Sorun giderme

Sık karşılaşılan sorunlar ve çözümleri. İndirme hatalarının çoğu ilk iki maddeden birine dayanır.

## Açık içerikli bir parça indirilmiyor

**Belirti** — indirme başarısız olur ve kuyruk, parçanın yaş sınırlı olduğuna dair bir mesaj ya da (eski sürümlerde) şuna benzer ham bir hata gösterir:

```
Error: ERROR: [youtube] <id>: Sign in to confirm your age.
This video may be inappropriate for some users.
```

**Neden** — YouTube yaş sınırlı (açık içerikli) parçaları yalnızca oturum açmış yetişkin bir hesaba sunar. Downtify varsayılan olarak anonim indirir; bu yüzden YouTube reddeder.

**Çözüm** — YouTube çerezleri sağlayın: **Ayarlar** (⚙️) → **YouTube çerezleri** → **cookies.txt yükle**. Dosyanın nasıl dışa aktarılacağı için [YouTube çerezleri](features/youtube-cookies.md) sayfasına bakın.

Çerezler yapılandırılmış olduğu halde yine başarısız oluyorsa çerezler eskimiştir ya da hesabın kendisi Google’ın yaş doğrulamasını tamamlamamıştır. Doğrulanmış bir hesapta oturum açmış bir tarayıcıdan yeni bir dosya dışa aktarın ve yeniden yükleyin.

## İndirmeler başarısız oluyor, zaman aşımına uğruyor ya da hiç başlamıyor

**Belirti** — indirmeler görünürde sıradan parçalar için başarısız olur; bazen “Bot olmadığınızı doğrulamak için oturum açın” ya da bir biçim/çıkarma hatasıyla.

**Neden** — YouTube, otomatik saydığı istekleri kısıtlar ve zorlar. Bu, bir VPS’te veya VPN arkasında ev bağlantısına göre çok daha yaygındır.

**Çözüm**, ne sıklıkta işe yaradığına göre sırayla:

1. **Bir `cookies.txt` yükleyin** ([YouTube çerezleri](features/youtube-cookies.md)). Kimliği doğrulanmış bir oturum çok daha seyrek zorlanır. Bu, tek başına en etkili düzeltmedir.
2. **İndirmeler arasına bekleme ekleyin** — **Ayarlar** → *İndirmeler arası bekleme* (5–15 sn deneyin) ve *Eşzamanlı indirmeleri* düşürün. YouTube’u bir anda koca bir çalma listesiyle yormak hız sınırlamasını tetikler.
3. **IPv4’ü zorlayın** — ana makineniz IPv6 duyuruyor ama gerçekte yönlendiremiyorsa `DOWNTIFY_FORCE_IPV4=1` ayarlayın (DNS/`EAI_AGAIN` hataları olarak görünür).
4. **İmajı güncelleyin** — `docker compose pull && docker compose up -d`. YouTube savunmalarını sık değiştirir ve her sürüm daha yeni bir `yt-dlp` getirir.

## Windows / Docker Desktop’ta bir cookies.txt algılanmıyor

**Belirti** — `DOWNTIFY_COOKIES_FILE` ayarlı ama Downtify çerez yokmuş gibi davranıyor.

**Neden** — yol bir *kapsayıcı* yoludur. `C:\Users\me\cookies.txt` gibi bir Windows yolu kapsayıcının içinde bir anlam taşımaz ve değişkenin ona işaret edebilmesi için dosyanın önce bağlanması gerekir.

**Çözüm** — değişkeni tamamen bırakın ve dosyayı **Ayarlar** → **YouTube çerezleri** üzerinden yükleyin. Bu yol bağlama gerektirmez ve her platformda aynı çalışır.

Değişkeni tutmayı tercih ederseniz dosyayı bağlayın ve ana makine yolunu değil, bağlama hedefini gösterin:

```yaml
volumes:
  - ./cookies.txt:/cookies.txt:ro
environment:
  - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

## Çerez yükleme düğmesi soluk

`DOWNTIFY_COOKIES_FILE` ayarlı; bu yüzden o dağıtım kendi çerez dosyasını yönetir ve web arayüzü bilerek salt okunur kalır. Çerezleri arayüzden yönetmek için değişkeni kaldırın (ve kapsayıcıyı yeniden oluşturun).

## Yüklenen çerezler kapsayıcı güncellendikten sonra kayboldu

Yüklenen dosya Downtify’ın veri dizininde (`/data`) bulunur. Bu dizin adlandırılmış bir birim ya da bağlama noktası değilse, kapsayıcı yeniden oluşturulduğunda içindeki her şey — ayarlar ve Çalma Listesi İzleyici veritabanı dahil — kaybolur:

```yaml
volumes:
  - ./downloads:/downloads
  - downtify_data:/data   # ← bunu koruyun
```

## Yüklerken “cookies.txt is invalid”

Downtify dosyayı yüklerken doğrular. Dosya bir **Netscape** çerez deposu olmalıdır: satır başına bir çerez, alanlar sekmeyle ayrılmış, isteğe bağlı `#` yorumlarıyla. JSON dışa aktarımı, bir elektronik tablo ya da kopyalanmış bir `Cookie:` başlığı reddedilir.

Netscape biçiminde dışa aktaran bir tarayıcı eklentisi kullanın ([YouTube çerezleri](features/youtube-cookies.md) sayfasına bakın) ve sekme `youtube.com` üzerindeyken dışa aktarın.

## Bir çalma listesi zaten sahip olduğum parçaları yeniden indiriyor

Downtify otomatik indirilen her parçayı veritabanına kaydeder; bu yüzden dosyaları diskte başka bir yere taşımak yeniden indirmeyi tetiklemez. Bir parça, ancak saatlik bir kontrol dosyasının indirme dizininden gerçekten kaybolduğunu bulduktan sonra yeniden indirilir. [Çalma Listesi İzleyici](features/playlist-monitor.md#how-it-works) sayfasına bakın.

Dosyalar her yeniden başlatmada kayboluyorsa `/downloads` birimi kalıcı değildir — çözüm yukarıdakiyle aynı.

## “Could not find a YouTube match for '…'”

Ne YouTube Music ne de standart YouTube, eşleştiricinin denetimlerini geçen bir sonuç döndürdü — kaynağa benzeyen başlık, en az bir ortak sanatçı, karaoke/cover/canlı/başka dil sürümü olmama ve Spotify’ınkinin 30 saniye içinde bir süre. [Nasıl çalışır](how-it-works.md#fallback-to-standard-youtube) sayfasına bakın.

Bu genellikle şarkının gerçekten YouTube’da olmadığı ya da çok farklı bir başlık veya sanatçı kredisiyle yüklendiği anlamına gelir. Doğru videoyu kendiniz bulabiliyorsanız, tam o videoyu indirmek için YouTube URL’sini arama çubuğuna yapıştırın.

## İndirilen sesin meta verisi veya kapağı yanlış

Downtify meta verileri Spotify’dan çözümler ve sesi YouTube Music’te eşleştirir. Uyumsuzluk genellikle eşleşmenin bir cover, remix veya canlı sürüme düştüğü anlamına gelir. Bir arama sonucu yerine Spotify’ın **albüm** bağlantısından indirmek, eşleştiriciye çok daha fazla bilgi verir (parça numarası, albüm, yayın türü).

## Hâlâ takıldınız mı?

[github.com/henriquesebastiao/downtify/issues](https://github.com/henriquesebastiao/downtify/issues) adresinde şunlarla bir issue açın:

- Downtify sürümü (kenar çubuğunun altında ve **Ayarlar → Hakkında** içinde görünür),
- hatanın çevresindeki kapsayıcı günlükleri (`docker compose logs downtify`),
- ve çerezlerin yapılandırılıp yapılandırılmadığı.
