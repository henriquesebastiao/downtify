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
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Ayarlandığında ayarlar ekranı çerez bölümünü kilitli gösterir ve yükleme ile silmeleri reddeder — o yapılandırmanın sahibi dağıtımdır ve Downtify yönetmediği bir dosyanın üzerine yazmamalıdır. Çerezleri bunun yerine web arayüzünden yönetmek için değişkeni kaldırın (ve kapsayıcıyı yeniden oluşturun).

`DOWNTIFY_COOKIES_FROM_BROWSER` çerezleri doğrudan bir tarayıcı profilinden okur, ancak bu, tarayıcının çerez deposunun kapsayıcının *içinden* erişilebilir olmasını gerektirir; bu yüzden Docker’da nadiren kullanılabilir.

## Çalışır tutma

- Çerezlerin süresi dolar. Yaş sınırlı indirmeler yeniden başarısız olmaya başlarsa yeni bir dosya dışa aktarıp yerine yükleyin.
- Sonra kapattığınız bir **gizli pencereden** dışa aktarmak daha uzun ömürlü bir oturum üretir, çünkü normal bir pencereyi kapatmak dışa aktarılan oturumu geçersiz kılabilir.
- Bazı bölgeler, YouTube yaş sınırlı içeriği sunmadan önce Google hesabında tam kimlik doğrulaması ister. Oturum açmış olmak her zaman yetmez.

::: warning Dosyaya bir parola gibi davranın
Bir `cookies.txt`, Google hesabınızın canlı oturum belirteçlerini içerir. Onu okuyabilen herkes YouTube’da sizin adınıza hareket edebilir. Downtify onu dosya sisteminin desteklediği yerde yalnızca sahibine açık izinlerle saklar ve içeriğini API üzerinden asla göstermez — yalnızca yapılandırılmış olup olmadığını, boyutunu ve ne zaman değiştiğini. Ana hesabınızı riske atmak istemiyorsanız tek kullanımlık bir Google hesabı kullanın.
:::
