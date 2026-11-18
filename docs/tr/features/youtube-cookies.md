---
icon: lucide/cookie
---

# YouTube çerezleri

Downtify sesini YouTube’dan alır. Çoğu zaman bu anonim olarak çalışır — ama her zaman değil:

- **Açık içerikli / yaş sınırlı parçalar.** YouTube bunları yalnızca oturum açmış yetişkin bir hesaba sunar. Çerez olmadan indirme başarısız olur.
- **Bot doğrulamaları.** Veri merkezi IP’lerinde (VPS, bazı VPN’ler) YouTube ses yerine zaman zaman “Bot olmadığınızı doğrulamak için oturum açın” yanıtı verir.

Bir `cookies.txt` sağlamak ikisini de çözer: yt-dlp o zaman YouTube ile oturum açmış tarayıcı oturumunuzun yaptığı gibi konuşur.

## cookies.txt yükleme (önerilir)

1. Bir çerez dışa aktarma eklentisi kurun: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge) veya [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
2. `youtube.com`’u **Google hesabınızda oturum açmışken** açın ve o sitenin çerezlerini dışa aktarın — dosya **Netscape** biçiminde olmalıdır
3. Downtify’da **Ayarlar**’ı (⚙️) açın → **YouTube çerezleri** → **cookies.txt yükle**

Dosya yüklenirken doğrulanır — Netscape çerez deposu olmayan bir dosya, sonraki tüm indirmeleri sessizce bozmak yerine hemen reddedilir. İçinde `youtube.com` veya `google.com` çerezi yoksa uyarı alırsınız; bu genellikle yanlış sekmeden dışa aktarıldığı anlamına gelir.

Yüklendikten sonra aynı ekrandan onu **değiştirebilir** (başka bir dosya yükleyerek) veya **silebilirsiniz**.

::: tip Bu, platformdan bağımsız yoldur
Web arayüzünden yüklemek bağlama noktası, dosya yolu ya da kabuk gerektirmez — bu da bir `cookies.txt` dosyasını kapsayıcıya bağlamanın kötü şöhretli biçimde zahmetli olduğu Windows için Docker Desktop’ta çalışmasını sağlar.
:::

## Nerede saklanır

Yüklenen dosya, Downtify’ın veri dizininde (varsayılan `/data`) `cookies.txt` olarak yazılır — `settings.json` ve Çalma Listesi İzleyici veritabanını tutan aynı birim. Bu yüzden **kapsayıcı güncellemelerinden etkilenmez**: yeni bir imaj çekip kapsayıcıyı yeniden oluşturmak, `/data` adlandırılmış bir birim veya bağlama noktası olarak kaldığı sürece çerezlerinizi korur.

## Bunun yerine ortam değişkeni kullanma

Önceden var olan [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube) değişkeni hâlâ çalışır ve **önceliklidir**:

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Bakımın yenilenen çerezleri içine kaydedebilmesi için dosyayı yazılabilir bağlayın (`:ro` olmadan); salt okunur bir dosya yine kullanılır ama eskisi gibi bayatlar.

Ayarlandığında ayarlar ekranı çerez bölümünü kilitli gösterir ve yükleme ile silmeleri reddeder — o yapılandırmanın sahibi dağıtımdır ve Downtify yönetmediği bir dosyanın üzerine yazmamalıdır. Çerezleri bunun yerine web arayüzünden yönetmek için değişkeni kaldırın (ve kapsayıcıyı yeniden oluşturun).

`DOWNTIFY_COOKIES_FROM_BROWSER` çerezleri doğrudan bir tarayıcı profilinden okur, ancak bu, tarayıcının çerez deposunun kapsayıcının *içinden* erişilebilir olmasını gerektirir; bu yüzden Docker’da nadiren kullanılabilir.

## Çalışır tutma

Dışa aktarılan çerezler belirli bir tarihte sona ermez. Google oturumu sürekli değişen çerezlerden oluşur: çerezlerin alındığı sekme `__Secure-1PSIDTS`, `SIDCC` ve benzerlerini birkaç dakikada bir yeniler; yeni değerleri hiç öğrenmeyen bir kopya sonunda reddedilir. yt-dlp bu durumda "The provided YouTube account cookies are no longer valid" kaydını düşer. VPN'de veya veri merkezi IP'sinde YouTube daha katıdır, bu yüzden bu birkaç saat içinde olabilir.

Downtify yüklenen dosyanın oturumunu kendisi açık tutar:

- **Her indirme yeni değerleri kaydeder.** yt-dlp her indirme için dosyanın özel bir kopyasını alır; indirme bitince YouTube'un bu sırada değiştirdiği çerezler kayıtlı `cookies.txt` dosyasına geri yazılır ve başka bir indirmenin bu arada kaydettiği daha yeni bir değer geri alınmaz.
- **Bakım onları düzenli olarak yeniler.** Her 15 dakikada bir (`DOWNTIFY_COOKIES_REFRESH_MINUTES`, `0` kapatır) Downtify, tarayıcının yaptığı isteğin aynısıyla Google'dan oturum çerezlerini yenilemesini ister, onlarla `youtube.com`'u açar ve değişeni kaydeder. Günlerce hiçbir şey indirmeyen bir sunucu bile oturumunu canlı tutar.
- **Ayarlar ekranı sonucu gösterir.** **Ayarlar → YouTube çerezleri**; *Oturum açık*, *Oturum kapandı*, *Hesap yok* (dosyada Google oturumu yok, yalnızca ziyaretçi çerezleri var) veya *Denetim başarısız* durumunu, son denetimin ne zaman yapıldığını ve YouTube'un en son ne zaman bot denetimi istediğini gösterir. *Şimdi denetle* bakımı hemen çalıştırır. Yeni yüklenen dosya kaydedildikten birkaç saniye sonra denetlenir.

Size kalanlar:

- **Gizli pencereden dışa aktarın ve pencereyi kapatın.** Gizli bir pencerede YouTube'a giriş yapın, aynı sekmede `youtube.com/robots.txt` adresini açın, çerezleri dışa aktarın ve pencereyi kapatın. Kullanmaya devam ettiğiniz bir sekme oturumu kendisi yeniler ve Downtify'ın kopyasının oturumu dakikalar içinde kapanır. Mümkünse aynı hesabı aynı anda normal bir pencerede kullanmayın.
- **Ekranda *Oturum kapandı* yazınca yeni bir dosya yükleyin.** Google oturumu yine de sonlandırabilir (parola değişikliği, "tüm cihazlardan çıkış", güvenlik incelemesi). Günlük de bunu söyler: `YouTube cookies are signed out`.
- Bazı bölgeler, YouTube yaş kısıtlamalı herhangi bir içerik sunmadan önce Google hesabında tam kimlik doğrulaması ister. Oturum açık olması her zaman yetmez.

::: info Neden "Google ile oturum aç" düğmesi yok
Downtify sizin yerinize Google'a giriş yapamaz. Google betikle ve headless tarayıcıyla yapılan girişleri engeller ("Bu tarayıcı veya uygulama güvenli olmayabilir"), iki adımlı doğrulama ve cihaz onayı ister; YouTube da artık yt-dlp gibi üçüncü taraf istemcilerden OAuth kabul etmiyor. Downtify'da bir giriş formu, Google parolanızı ona vermek anlamına da gelirdi. Otomatikleştirilebilen kısım, dışa aktarılmış bir oturumu canlı tutmaktır.
:::

::: tip Hesapsız bot denetimleri
"Sign in to confirm you're not a bot" eksik çerezlerden değil, IP adresinden kaynaklanır. VPN'de sürekli çıkıyorsa VPN sunucusunu veya çıkış ülkesini değiştirmek çoğu zaman yeni çerezlerden daha çok işe yarar. Çok sayıda indirmede kullanılan çerezler YouTube'un o hesabı kısıtlama ihtimalini de artırır; bu yüzden kullan-at bir hesap daha güvenli seçimdir.
:::

::: warning Dosyaya bir parola gibi davranın
Bir `cookies.txt`, Google hesabınızın canlı oturum belirteçlerini içerir. Onu okuyabilen herkes YouTube’da sizin adınıza hareket edebilir. Downtify onu dosya sisteminin desteklediği yerde yalnızca sahibine açık izinlerle saklar ve içeriğini API üzerinden asla göstermez — yalnızca yapılandırılmış olup olmadığını, boyutunu ve ne zaman değiştiğini. Ana hesabınızı riske atmak istemiyorsanız tek kullanımlık bir Google hesabı kullanın.
:::
