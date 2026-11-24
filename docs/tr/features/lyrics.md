---
icon: lucide/mic-vocal
---

# Şarkı sözleri

Downtify, bir parça indirilirken sözleri arar ve dosyaya gömer; zamanla eşzamanlıysa ayrıca bir `.lrc` yan dosyası da yazar.

## Sözleri açma

Sözler **varsayılan olarak açıktır**. **Ayarlar → Etiketler ve sözler → Şarkı sözlerini indir** içinden kapatın.

## Sağlayıcılar ve yedek sırası

Kataloglar farklıdır: bir sağlayıcının hiç duymadığı şarkı çoğu zaman başka birindedir. Bu yüzden Downtify sıralı bir sağlayıcı listesi tutar ve bir şey bulan ilkinde durarak onları tek tek dener.

| Sağlayıcı | Sözler | Notlar |
|----------|--------|-------|
| **[LRCLIB](https://lrclib.net)** | Düz ve zamanla eşzamanlı | Ücretsiz topluluk veritabanı, anahtar yok. Başlık, ana sanatçı, albüm ve süreyle eşleştirilir. Bu yolla zaman eşlemeli bir şey bulunmazsa araması da denenir; başlık, sanatçı ve süre (birkaç saniye içinde) uyuyorsa sonuç kabul edilir. |
| **NetEase Cloud Music** | Genellikle zamanla eşzamanlı | Büyük katalog; Asya yayınlarında güçlü, çoğu zaman Batı yayınlarında da. Başlık, sanatçı ve süreyle eşleştirilir; sanatçısı farklı yazılmış bir sonuç (örneğin geleneksel ve basitleştirilmiş Çince) yalnızca başlık ve süre ikisi de tuttuğunda kabul edilir. |
| **Kugou Music** | Zaman eşlemeli | Geniş katalog, Çin yayınlarında güçlü ve birçok Batılı yayın da var. NetEase gibi eşleştirilir; baştaki başlık satırı ve söz yazarı bilgileri atılır. |

**Ayarlar → Etiketler ve sözler → Sağlayıcılar** içinde sağlayıcıları tercih ettiğiniz sıraya sürükleyebilir ya da oklarla taşıyabilir ve herhangi birini kapatabilirsiniz. En az biri açık kalır; söz aramayı tamamen durdurmak için **Şarkı sözlerini indir** anahtarını kullanın. Kendi listeni zaten kaydettiysen, bir güncellemeyle eklenen sağlayıcı kapalı başlar: onu orada aç.

### Yalnızca zaman eşlemeli sözler

**Ayarlar → Etiketler ve şarkı sözleri → Yalnızca zaman eşlemeli şarkı sözleri** (varsayılan olarak kapalı) yalnızca zaman damgalı sözleri tutar: bir sağlayıcının şarkı için yalnızca düz sözü varsa hiç yok sayılır ve sonraki sağlayıcıya sorulur. [Kitaplığı yükselt](library-upgrade.md) de yalnızca düz sözü olan bir parçayı sözsüz sayar. Bir dosyanın zaten sahip olduğu zaman eşlemeli sözler her zaman sayılır: yanındaki bir `.lrc` dosyası, etiketlerdeki zaman damgalı sözler veya bir ID3 `SYLT` çerçevesi (diğer uygulamalardan gelen dosyalarda bazen olduğu gibi). Ayar açıkken Downtify'ın bulduğu zaman eşlemeli sözler düz sözlerin yerini alır: `.lrc` dosyasında ve dosyanın kendi söz etiketinde, böylece yalnızca etiketleri okuyan oynatıcılar da sözleri eşlemeli gösterir. Tarama, sözü eksik parçalardan kaçında yalnızca düz söz olduğunu da söyler.

### Sözü olmayan parçalar için söz bulma

**Kitaplık → Kitaplığı yükselt → Tara ve söz bul** kitaplıkta sözü olmayan parçaları tarar ve hemen söz arar, ilerleme çubuğuyla. Sonunda kaç parçaya söz eklendiğini, kaçı için bulunamadığını ve kaçının başarısız olduğunu söyler. Bkz. [Kitaplığı yükselt](library-upgrade.md#while-it-runs).

::: info Peki Genius, Musixmatch ve AZLyrics?
Kullanılamıyorlar ve Downtify artık sunmuyor:

- **AZLyrics**, sözlerinin sayfanın kendisinde üçüncü taraflarca kullanılmasını yasaklar.
- **Musixmatch**’in masaüstü API’si, uygulamalara vermediği kimlik bilgilerine sahip olmadıkça boş bir belirteçle yanıt verir.
- **Genius**’un `robots.txt` dosyası, bir şarkının sayfasını bulmak için gereken arama uç noktasına izin vermez.

Hâlâ bu adları içeren kayıtlı ayarlar çalışmaya devam eder: adlar yok sayılır ve başka hiçbir şey kalmayan liste varsayılan sağlayıcılara döner.
:::

## Hiçbir şeyi olmayan sağlayıcıları atlama

Bir aramanın ardından Downtify her şarkı için hangi sağlayıcıların yanıt verdiğini ve hangilerinin boş döndüğünü `/data` altındaki `downtify_library.db` içinde kaydeder.

Bir şarkı için hiçbir şeyi olmayan sağlayıcıya, yeniden indirmeler ve büyük kitaplık taramaları aynı başarısız aramaları tekrarlamasın diye **30 gün** boyunca o şarkı sorulmaz. Sonra, kataloglar büyüdüğü için yeniden denenir. Sözleri *olan* bir sağlayıcı asla atlanmaz; böylece yeniden indirilen bir dosya sözlerini geri alır.

## Gömme

| Biçim | Düz söz etiketi | Eşzamanlı söz etiketi |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | Zaman damgalı `USLT` |
| FLAC | `LYRICS` (Vorbis yorumu) | LRC içerikli `LYRICS` |
| M4A | `©lyr` | LRC içerikli `©lyr` |
| OGG / OPUS | `LYRICS` (Vorbis yorumu) | LRC içerikli `LYRICS` |

## .lrc yan dosyası

Eşzamanlı sözler olduğunda Downtify ayrıca bir `.lrc` dosyası kaydeder. Varsayılan olarak aynı temel adla **sesin yanında** durur. **Ayarlar → Etiketler ve sözler** içinde bunu kapatıp onun yerine bir **söz klasörü** seçebilirsiniz (varsayılan `/data/lyrics`). Bu klasör `/downloads`, slskd ağacı ve ek müzik klasörlerinin **dışında** olmalıdır — sesin göreli yolu altında yeniden oluşturulur (`Sanatçı/Albüm/parça.lrc`). Harici sözleri okuyan oynatıcılar (ve [yerleşik oynatıcı](player.md#now-playing)) yan dosyayı yine bulur. Bu ayarı değiştirip bir ek klasörde **Eşitle**’yi çalıştırmak mevcut `.lrc` dosyalarını yeni konuma kopyalar; kaynak dosya o ağaç yazılabilirse kaldırılır, salt okunur bir bağlamada yerinde bırakılır. Sözler etiketlere zaten gömülü olsa bile yan dosya yazılır.

Parçayı Kitaplık sayfasından silmek, `.lrc` dosyasını (dosyanın yanındakini ve ayrılmış klasördekini) sesle birlikte kaldırır; böylece sözler hiçbir zaman sahipsiz bir dosya olarak kalmaz.

## Zamanlamayı ayarlama

İnternette bulunan sözler bazen indirilen sese göre biraz erken ya da geç kalır: şarkının başka bir versiyonu, daha uzun bir giriş. Bir şarkıyı düzeltmek için onu çalın, **Şimdi çalıyor → Şarkı sözleri** bölümünü açın ve sözlerin sağ üstündeki kronometre düğmesine, **Söz zamanlamasını ayarla** düğmesine basın:

- **−** sözleri daha erken, **+** daha geç gösterir; her basışta saniyenin onda biri, her iki yönde en fazla bir dakika. Sözler yeni zamanlamayı hemen izler, böylece şarkı çalarken deneyebilirsiniz.
- **Kaydet** ayarı şarkının dosyalarına yazar; **Sıfırla** kayıtlı zamanlamaya döner.

Kaydetmek zaman damgalarının kendisini yeniden yazar: `.lrc` dosyasında ve dosyanın etiketlerinde zamanlı sözler varsa onlarda da (MP3 `SYLT` çerçeveleri dahil). Böylece düzeltme `.lrc` dosyasını ya da etiketleri okuyan diğer oynatıcılarda ve uygulamalarda da görünür. Salt okunur bir dosya etiketlerini korur; yalnızca `.lrc` değişir. Bir `.lrc` içindeki `[offset:N]` satırı kaydederken zamanlara katılır; Downtify oynatıcısı ise ona o zamana kadar da uyar.

Düğme yalnızca zamanlı sözleri olan kütüphane şarkılarında görünür. Oturum açmış her kullanıcı ayarlayabilir; değişiklik [etkinlik günlüğünde](users.md#activity) **Söz zamanlaması ayarlandı** olarak görünür. Endpoint: [`POST /api/library/lyrics/offset`](../api-reference.md#post-apilibrarylyricsoffset).

## Hiçbir şey bulunamazsa

Hiçbir sağlayıcıda şarkı yoksa indirme normal şekilde sürer — ses dosyası sözsüz kaydedilir ve hata oluşmaz.
