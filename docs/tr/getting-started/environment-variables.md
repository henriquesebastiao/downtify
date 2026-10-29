---
icon: lucide/settings
---

# Ortam değişkenleri

Tüm ortam değişkenleri isteğe bağlıdır. Downtify hiçbiri olmadan kutudan çıktığı gibi çalışır.

## Temel

| Değişken | Varsayılan | Açıklama |
|----------|---------|-------------|
| `DOWNTIFY_PORT` | _(ayarlı değil)_ | Sunucunun (kapsayıcının içinde) dinlediği bağlantı noktası. Ayarlı değilse: **Ayarlar → Sunucu → Port** içinde seçilen bağlantı noktası, yoksa `8000`. Ayarlıysa önceliklidir ve Ayarlar’daki alan kilitlenir. Farklı bir ana makine bağlantı noktası sunmak için bağlantı noktası eşlemesinin sol tarafını değiştirin. [Bağlantı noktasını değiştirme](../features/server.md#changing-the-port) bölümüne bakın. |
| `DOWNLOAD_DIR` | `/downloads` | Ses dosyalarının kaydedildiği dizin. Kitaplığınızı özel bir yola bağlıyorsanız değiştirin. |
| `HOST` | `0.0.0.0` | Web sunucusunun bağlanma adresi. |
| `DOWNTIFY_LOG_LEVEL` | `info` | Uygulama günlük düzeyi (`debug`, `info`, `warning`, …). |
| `TZ` | `UTC` | Aşağıdaki `DOWNTIFY_MONITOR_SYNC_TIME` değerini yorumlamak için kullanılan yerel saat dilimi (IANA adı, örn. `America/Sao_Paulo`). |

## Çalma Listesi İzleyici

| Değişken | Varsayılan | Açıklama |
|----------|---------|-------------|
| `DOWNTIFY_MONITOR_SYNC_TIME` | _(ayarlı değil)_ | Günlük veya daha uzun aralıklı (her gün, hafta, 2 hafta, ay) [Çalma Listesi İzleyici](../features/playlist-monitor.md#choosing-a-daily-sync-time) eşitlemelerinin çalışması gereken günün saati (24 saatlik `HH:MM`, yukarıdaki `TZ`’ye göre yerel). Önceki kontrolden tam bir aralık sonra, hangi saate denk gelirse gelsin eşitlemek için ayarsız bırakın. |

```yaml
environment:
  - TZ=America/Sao_Paulo
  - DOWNTIFY_MONITOR_SYNC_TIME=03:00
```

## Mobil uygulamalar ve oturum açma

[Mobil uygulamalar](../features/mobile-apps.md) ve [Kullanıcılar ve oturum açma](../features/users.md) sayfalarına bakın. `DOWNTIFY_DISABLE_AUTH` `true` olmadıkça oturum açmak zorunludur; önceki sürümlerdeki `DOWNTIFY_REQUIRE_SIGN_IN` artık kullanılmaz (ayarlı olduğu sürece günlüğe bir uyarı yazılır).

| Değişken | Varsayılan | Açıklama |
|----------|---------|-------------|
| `DOWNTIFY_DISABLE_AUTH` | `false` | `true` hesapları kapatır: kimse oturum açmaz ve sunucuya ulaşan herkes onu yönetici olarak kullanır. Oturum açma sayfası, çıkış düğmeleri, **Ayarlar → Kullanıcılar** ve **Ayarlar → Genel**’in hesap kısmı kaybolur. Eşleştirilmiş uygulamalar çalışmaya devam eder. Tekrar `false` yapın (ya da kaldırın), oturum açma yeniden zorunlu olur ve hesaplar eskisi gibi durur. [Kullanıcılar ve oturum açma](../features/users.md#turning-accounts-off) sayfasına bakın. |
| `DOWNTIFY_TRUSTED_PROXIES` | _(ayarlı değil)_ | Ters proxy’nizin virgülle ayrılmış adresleri veya ağları (örn. `172.18.0.0/16,10.0.0.5`). Yalnızca bunlardan gelen isteklerin `X-Forwarded-For`, `X-Forwarded-Proto` ve `X-Forwarded-Host` başlıklarına inanılır — oturum açma ve eşleştirme denemelerinin sınırlandığı istemci adresi, oturum çerezindeki secure bayrağı ve aynı site denetimi için. Ayarlı değilse: bu başlıklar yok sayılır. |
| `DOWNTIFY_DISCOVERY` | `true` | `false`, uygulamaların *Bu ağda bulundu* altında listelemek için kullandığı sunucu duyurusunu yerel ağda (mDNS, `_downtify._tcp`) durdurur. Docker’ın köprü ağında duyuru zaten LAN’a ulaşmaz — [Docker Compose](docker-compose.md#finding-the-server-from-the-apps) sayfasına bakın. |
| `DOWNTIFY_TRANSCODE_CACHE_MB` | `2048` | Dönüştürülmüş kopyaların önbelleğinin (`/data/transcode_cache`) altında tutulduğu en büyük boyut, MB cinsinden; en uzun süredir çalınmayan kopyalar önce gider. |
| `DOWNTIFY_TRANSCODE_CONCURRENCY` | `2` | Uygulamaların daha küçük akış kaliteleri için aynı anda kaç şarkının dönüştürüldüğü. |
| `DOWNTIFY_STREAM_CACHE_MB` | `1024` | Akıtılan sesin önbelleğinin (`/data/stream_cache`) altında tutulduğu en büyük boyut, MB cinsinden; en uzun süredir çalınmayan kopyalar önce gider. Sunucu üzerinden akış, tarayıcının YouTube’a ulaşamadığı yerlerde indirilmemiş parçaları çalan şeydir. |
| `DOWNTIFY_STREAM_CONCURRENCY` | `2` | Aynı anda kaç akış indirmesinin çalışabileceği. |

## Müzik çöp kutusu

Bkz. [Müzik çöp kutusu](../features/music-trash.md). Bunlardan biri ayarlanmadıkça kapalıdır.

| Değişken | Varsayılan | Açıklama |
|----------|---------|-------------|
| `DOWNTIFY_TRASH` | `false` | `true`, indirme klasörü için müzik çöp kutusunu açar: kaldırılan parçalar 30 gün saklanan bir çöp kutusuna taşınır ve dosyaları Downtify kendisi taşır. Açıkken parçaları yalnızca yöneticiler kaldırabilir. |
| `DOWNTIFY_TRASH_CONFIG` | _(ayarlı değil)_ | Çöp kutusunun kapsadığı klasörleri ve çalışanının nerede çalıştığını (`embedded` veya `external`) listeleyen JSON dosyasının konteyner içindeki yolu. `DOWNTIFY_TRASH` ayarının önüne geçer. Okunamayan bir dosya sunucunun başlamasını engeller. Bkz. [Yapılandırma dosyası](../features/music-trash.md#the-configuration-file). |

## Sağlık denetimi

İmajda yerleşik bir [Docker `HEALTHCHECK`](https://docs.docker.com/reference/dockerfile/#healthcheck) vardır — özel bir `--health-cmd` gerekmez. Kapsayıcının kendi bağlantı noktasında her 30 saniyede bir `GET /api/health`’i sorgular (5 saniye zaman aşımı, 20 saniye başlangıç toleransı, kapsayıcı sağlıksız işaretlenmeden önce 3 deneme). `docker ps` ve `docker inspect` sonucu gösterir; Compose’un `condition: service_healthy` değeri veya Watchtower gibi araçlar buna göre hareket edebilir.

| Değişken | Varsayılan | Açıklama |
|----------|---------|-------------|
| `DOWNTIFY_HEALTHCHECK` | `1` | Yerleşik denetimi kapatmak için `0` yapın — o zaman sunucuya hiç bağlanmadan her zaman sağlıklı bildirir. Kapsayıcı sağlığına yalnızca harici/orkestratör düzeyindeki bir denetimin (örn. bir Kubernetes liveness probe) karar vermesini istiyorsanız kullanın. |

```yaml
environment:
  - DOWNTIFY_HEALTHCHECK=0
```

## Anti-bot / YouTube

YouTube otomatik indiricileri düzenli olarak zorlar. Bu değişkenler, varsayılanlar çalışmayı bıraktığında size kaçış yolları verir.

| Değişken | Varsayılan | Açıklama |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(ayarlı değil)_ | yt-dlp’yi yalnızca IPv4 kullanmaya zorlamak için `1` yapın. Ana makinenizin IPv6 adresi bozuk veya hız sınırlıysa işe yarar. |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | Denenecek yt-dlp oynatıcı istemcilerinin virgülle ayrılmış, sıralı listesi. Downtify’ın varsayılan listesi zaten JavaScript çalışma zamanı olmadan çalışan istemcileri tercih eder. Yalnızca belirli bir istemcinin engellendiğini biliyorsanız değiştirin. |
| `DOWNTIFY_YT_PO_TOKEN` | _(ayarlı değil)_ | yt-dlp için virgülle ayrılmış Proof-of-Origin belirteçleri; her biri `<client>.<context>+<token>` biçiminde (örn. `mweb.gvs+ABC123`). Yalnızca YouTube kullandığınız istemciler için PO Token talep etmeye başlarsa gerekir. |
| `DOWNTIFY_COOKIES_FILE` | _(ayarlı değil)_ | **Kapsayıcının içindeki** Netscape biçimli bir `cookies.txt` yolu. yt-dlp’nin gerçek bir tarayıcı oturumu olarak kimlik doğrulamasını sağlar — açık içerikli/yaş sınırlı parçalar ve YouTube’un oturum açma duvarı uyguladığı her durum için gerekli. Web arayüzünde yüklenen bir dosyaya üstündür ve arayüzün o bölümünü salt okunur yapar. [YouTube çerezleri](../features/youtube-cookies.md) sayfasına bakın. |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(ayarlı değil)_ | Çerezlerin alınacağı tarayıcının adı (örn. `chrome`, `firefox`). Tarayıcının çerez deposunun kapsayıcı içinden erişilebilir olmasını gerektirir; bu yüzden Docker’da nadiren kullanılabilir. |

::: tip Muhtemelen bunlara ihtiyacınız yok
Web arayüzünde doğrudan **Ayarlar → YouTube çerezleri** içinden bir `cookies.txt` yükleyebilirsiniz. `/data` içinde saklanır (kapsayıcı güncellemelerinden etkilenmez), bağlama noktası veya kapsayıcı yolu gerektirmez ve Windows, macOS ve Linux’ta aynı çalışır. Yukarıdaki değişkenler, dosyayı kendileri yönetmeyi tercih eden dağıtımlar için desteklenmeye devam eder.
:::

## Örnek: anti-bot ayarlarıyla Docker Compose

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_FORCE_IPV4=1
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
    restart: unless-stopped
```

## Bir cookies.txt edinme

[Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome) veya [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox) gibi bir tarayıcı eklentisi kullanın. Gerçek bir Google hesabında oturum açmışken `youtube.com`’dan dışa aktarın, ardından dosyayı **Ayarlar → YouTube çerezleri** içinde yükleyin ya da yukarıda gösterildiği gibi kapsayıcıya bağlayın.

Tam anlatım için [YouTube çerezleri](../features/youtube-cookies.md) sayfasına, indirmeler yine de başarısız olursa [Sorun giderme](../troubleshooting.md) sayfasına bakın.

::: warning
`cookies.txt` dosyanızı gizli tutun — Google hesabınıza erişim sağlayan oturum belirteçleri içerir.
:::
