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
| **[LRCLIB](https://lrclib.net)** | Düz ve zamanla eşzamanlı | Ücretsiz topluluk veritabanı, anahtar yok. Başlık, ana sanatçı, albüm ve süreyle eşleştirilir. |
| **NetEase Cloud Music** | Genellikle zamanla eşzamanlı | Büyük katalog; Asya yayınlarında güçlü, çoğu zaman Batı yayınlarında da. Başlık, sanatçı ve süreyle eşleştirilir; sanatçısı farklı yazılmış bir sonuç (örneğin geleneksel ve basitleştirilmiş Çince) yalnızca başlık ve süre ikisi de tuttuğunda kabul edilir. |

**Ayarlar → Etiketler ve sözler → Sağlayıcılar** içinde sağlayıcıları tercih ettiğiniz sıraya sürükleyebilir ya da oklarla taşıyabilir ve herhangi birini kapatabilirsiniz. En az biri açık kalır; söz aramayı tamamen durdurmak için **Şarkı sözlerini indir** anahtarını kullanın.

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

## Hiçbir şey bulunamazsa

Hiçbir sağlayıcıda şarkı yoksa indirme normal şekilde sürer — ses dosyası sözsüz kaydedilir ve hata oluşmaz.
