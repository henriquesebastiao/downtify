---
icon: lucide/sliders-horizontal
---

# İndirme ayarları

Kenar çubuğundan **Ayarlar**’ı açın (telefonda: **Daha fazla → Ayarlar**). Sayfa bölümlere ayrılmıştır — Genel, Ses kaynakları, İndirmeler ve dosyalar, Etiketler ve sözler, Navidrome, Kitaplık ve Hakkında. Değişiklikler, altta beliren çubukta **Değişiklikleri kaydet**’e basana kadar bekletilir; kaydedilmemiş değişiklikler varken sayfadan ayrılmak önce sorar. Ayarlar diske kaydedilir ve kapsayıcı yeniden başlatmalarından etkilenmez.

## Biçim

| Biçim | Uzantı | Notlar |
|--------|-----------|-------|
| MP3 | `.mp3` | Varsayılan. Evrensel uyumluluk. |
| FLAC | `.flac` | Kayıpsız. Bit hızı ayarı yok sayılır. |
| M4A | `.m4a` | MPEG-4 kapsayıcısında AAC. Apple cihazları için iyi. |
| OGG | `.ogg` | Ogg Vorbis. Açık biçim, iyi kalite/boyut oranı. |
| OPUS | `.opus` | Düşük bit hızlarında en iyi sıkıştırma. |

## Bit hızı

Kayıplı biçimler (MP3, M4A, OGG, OPUS) için kullanılabilir. FLAC bu ayarı yok sayar.

| Seçenek | Kbps |
|--------|------|
| Düşük | 128 |
| Orta | 192 |
| Yüksek | 256 |
| En iyi | **320** (varsayılan) |

İndirilen ses, her kayıplı biçim için seçtiğiniz bit hızında kodlanır. YouTube’un sunduğu ses zaten hedef codec’e yaklaşık o bit hızında sahipse (örn. **M4A @ 128** için ~128 kbps AAC akışı), yeniden kodlanmak yerine olduğu gibi tutulur; çünkü yeniden kodlama yalnızca kalite kaybettirir.

::: info Daha yüksek bit hızı kalite katmaz
YouTube’un sesi en fazla yaklaşık **128–160 kbps**’e (AAC veya Opus) çıkar ve Downtify her zaman mevcut en iyi akışı indirir. Bunu 256 veya 320 kbps ile kodlamak, o kaynağı sadakatle koruyan daha büyük dosyalar verir ama kaynağın hiç sahip olmadığı ayrıntıyı geri getiremez. Dosya boyutu sizin için daha önemliyse daha düşük bir bit hızı seçin.
:::

## Çıktı dosya adı şablonu

Varsayılan dosya adı şablonu şudur:

```
{artists} - {title}
```

Bu, `The Night Owls - Do I Still Recall.mp3` gibi dosya adları üretir.

Kullanılabilir belirteçler:

| Belirteç | Açıklama |
|-------|-------------|
| `{title}` | Parça başlığı |
| `{artists}` | Virgülle ayrılmış sanatçı adları |
| `{album}` | Albüm adı |
| `{tracknumber}` | Parçanın albümündeki sırası, 2 haneye sıfırla tamamlanmış (örn. `01`, `12`). Kaynakta parça numarası yoksa boştur (örn. serbest metin/YouTube arama sonucu). |
| `{year}` | Yayın yılı (örn. `2025`). Kaynakta yayın tarihi yoksa boştur (örn. serbest metin/YouTube arama sonucu). |

Şablon, alt klasörler oluşturmak için `/` da içerebilir. Örneğin bir kitaplığı `Sanatçı/Albüm (2025)/01 - Başlık.mp3` olarak düzenlemek için — her albüm yayın yılıyla birlikte kendi klasörüne düştüğünden, tam bir diskografi indirirken işe yarar:

```
{artists}/{album} ({year})/{tracknumber} - {title}
```

::: info
Bu, aşağıdaki **Sanatçıya göre düzenle** / **Albüme göre düzenle** anahtarlarından bağımsızdır — onlar çalma listesi/albüm indirmelerini tüm kitaplığınızda paylaşılan sanatçı veya albüm klasörlerine yönlendirir. `{tracknumber}` ve `{year}`, yukarıdaki gibi bir şablonun aynı düzeni o anahtarları açmadan, parça parça elle kurmasına olanak tanır.
:::

## Eşzamanlı indirmeler

Aynı anda kaç şarkının indirileceğini belirler. Bir hazır değer (1, 2, 3, 5, 8) seçin ya da yanındaki sayı alanına **1 ile 30** arasında herhangi bir özel değer yazın.

| Değer | Davranış |
|-------|-----------|
| **1** | Sıralı — her seferinde bir şarkı (en güvenli, en düşük kaynak kullanımı) |
| **3** | Varsayılan. Hız ve kararlılık arasında iyi bir denge. |
| **8** | Büyük çalma listeleri için daha hızlı |
| **30’a kadar** | Çok hızlı bağlantılar için en iyisi; daha çok CPU ve bant genişliği kullanır, YouTube’un sizi hız sınırına takma olasılığını artırır. |

Sınır her toplu indirmeye — çalma listesi/albüm indirmeleri, toplu kuyruk uç noktası ve CSV [kitaplık içe aktarmaları](library-import.md) — ve **[Mevcut müzik klasörleri](external-library.md)** eşitleme aramalarına (sözler, kapaklar, tür) uygulanır. Yeni parçaları tek tek indiren Çalma Listesi İzleyici taramalarına **uygulanmaz**. Bu değeri Ayarlar’da değiştirmek yeniden başlatmadan hemen etkili olur; sunucu `1–30` dışındaki her değeri bu aralığa çeker.

## İndirmeler arası bekleme

Downtify’ın, istekleri arka arkaya ateşlemek yerine bir şarkıyı bitirdikten sonra sonrakine başlamadan önce yapılandırılabilir sayıda saniye beklemesini sağlar.

| Değer | Davranış |
|-------|-----------|
| **0** | Varsayılan — kapalı, gecikme yok. |
| **5 / 15 / 30 / 60** | Hazır değerler ya da **0 ile 300 saniye** arasında herhangi bir özel değer yazın. |

Çalma listesi, albüm ve toplu indirmelere, CSV [kitaplık içe aktarmalarına](library-import.md) ve Çalma Listesi İzleyici’nin otomatik taramalarına uygulanır. Tek bir elle parça indirmesinde atlanır (beklenecek “sonraki” şarkı yoktur) ve herhangi bir toplu işin *son* parçasından sonra da atlanır; böylece bir çalıştırma sonunda anlamsız bir beklemeyle bitmez.

Daha düşük bir **Eşzamanlı indirmeler** değeriyle birleştirildiğinde, büyük bir çalma listesini ya da içe aktarılmış bir kitaplığı gözetimsiz indirirken YouTube hız sınırından kaçınmanın ana aracıdır.

## Eşitleme aramaları arası bekleme

Aynı fikir, indirmeler yerine **[Mevcut müzik klasörleri](external-library.md)** için. Eşitleme, sözleri, eksik kapakları ve türü her seferinde **[Eşzamanlı indirmeler](#parallel-downloads)** kadar parçalık gruplar halinde arar, sonra bir sonraki gruptan önce bu kadar saniye bekler. Varsayılan **0** (aramalar eşzamanlı çalışmaya devam eder, yine de Eşzamanlı indirmeler ile sınırlıdır). LRCLIB, kapak kaynakları ve iTunes’a hepsi birden yüklenilmesin diye büyük bir koleksiyonda birkaç saniye kullanın.

## Kapakları indir

Downtify’ın albüm kapağını hiç gömüp gömmeyeceğini belirler. Varsayılan olarak açıktır. Kapak getirmeyi tamamen atlamak için kapatın — diğer tüm etiketler (başlık, sanatçı, albüm, yıl, söz) normal şekilde gömülmeye devam eder, ama kapak görüntüsü hiç istenmediği veya yazılmadığı için dosyalar küçülür ve biraz daha hızlı iner.

Bunu kapatmak, *Albüme göre düzenle* seçeneğinin (bkz. [Dosya düzeni](file-organization.md)) ürettiği ayrı `cover.jpg` dosyasının yazılmasını da atlar; [oynatıcı](player.md) ve kitaplık bu şekilde indirilen parçalar için kapak göstermez (bunun yerine yedek nota simgesi görünür).

Bu `cover.jpg`, albüm klasöründeki tüm parçalarca paylaşılır. Kitaplık sayfasından bir parçayı silmek onu da kaldırır, ama yalnızca o klasörde kalan **son** parça olduğunda — aynı albümden başka bir parça hâlâ oradaysa kapak kalır.

## Kapak çözünürlüğü

Yalnızca **Kapakları indir** (yukarıda) açıkken geçerlidir. Downtify’ın **YouTube Music** veya **Deezer** kaynaklı gömülü kapak için istediği hedef boyutu (piksel cinsinden genişlik ve yükseklik) belirler. Bir hazır değer (300, 600, 800, 1000, 1200) seçin ya da kaydırıcıyı **300 ile 1200** arasında herhangi bir yere sürükleyin; geçerli değer piksel olarak yanında gösterilir. Varsayılan 600’dür.

Kitaplığınızı Plex gibi, kapakları Downtify’ın varsayılan olarak gömdüğünden daha yüksek çözünürlükte gösteren bir medya sunucusuna beslerken kullanışlıdır.

İki kaynak ayarı farklı uygular, çünkü yalnızca biri gerçekten istek üzerine yeniden boyutlandırılabilir:

- **YouTube Music** küçük resimleri URL’leri düzenlenerek yeniden boyutlandırılabilir — gerçek CDN’de doğrulandı, yüksek hazır değerler çoğu albüm kapağı için (yalnızca büyütme değil) gerçekten daha fazla ayrıntı döndürür, kaynak görüntünün kendi çözünürlüğüne kadar.
- **Deezer**, herhangi bir parça, albüm, sanatçı veya çalma listesi kapağı için yalnızca dört sabit boyut sunar (56, 250, 500 ve 1000 px) — istenebilecek ara boyut yoktur. Downtify, bu dördünün yapılandırılan değerden en az o kadar büyük olan en küçüğünü seçer (300 px istemek 500 px olanı getirir, çünkü tam 300 px boyutu yoktur); 1000 px’ten fazlasını istemek de Deezer’ın en büyüğü olan 1000 px’i getirir.

::: info Spotify kaynaklı kapaklar etkilenmez
Downtify, Spotify’ın herkese açık embed API’sinin Spotify tarafından çözülen parçalar/albümler/çalma listeleri için sunduğu **en büyük** kapağı zaten gömer — istenebilecek daha büyük boyut yok. Bu ayar yalnızca YouTube Music (serbest metin araması, YouTube URL’leri ve sesin kendisi için YouTube Music ile yeniden eşleştirilen her Spotify parçası) veya Deezer (yapıştırılmış bir Deezer bağlantısı ya da [Listeler](charts.md)’den bir parça) üzerinden çözülen parçalar için tavanı yükseltir.
:::

Bu değeri Ayarlar’da değiştirmek, o an açık olan arama sayfası dahil hemen etkili olur — diskte zaten bulunan hiçbir şeyi yeniden indirmeyi gerektirmez.

## Var olan dosyaların üzerine yaz

Downtify’ın geçmiş davranışıyla uyumlu olarak varsayılan olarak açıktır: her indirme işlem hattından (ses getirme, etiketleme, kapak, söz) geçer ve hesaplanan çıktı yolunda zaten duran dosyanın üzerine yazar.

### “Tekrar”ın gerçekte ne anlama geldiği

Açıkken yeniden indirme, var olan dosyanın onarımı değil, **tamamen yeni bir çalıştırmadır**. Downtify elinizde ne olduğuna bakmaz: [ses kaynaklarınızı](#audio-provider) yapılandırılan sırayla arar — yani slskd ilkse, slskd yalnızca yedek olarak değil, önce denenir —, sesi yanıt veren kaynaktan getirir ve üzerine bugünün etiketlerini, kapağını ve sözlerini yazar.

Bunun, büyük bir kitaplığı yeniden indirmeden önce bilmeye değer bir sonucu var:

::: warning Farklı bir biçim eski dosyayı geride bırakır
Yeni dosya, [dosya adı şablonunun](#output-filename-template) ürettiği yola, **yeni** sesin uzantısıyla yazılır. Downtify eski dosyanın üzerine yalnızca ikisi de aynı uzantıda bittiğinde yazar.

Yani slskd bir FLAC ile yanıt verdiğinde `Sanatçı - Şarkı.mp3`’ü yeniden indirmek size **ikisini birden** verir: `Sanatçı - Şarkı.mp3` (eski, dokunulmamış) ve `Sanatçı - Şarkı.flac`. [slskd dosyalarını yerinde bırak](slskd-navidrome.md#leave-files-in-place) açıkken — varsayılan — slskd dosyası indirme klasörünüze bile kopyalanmaz; eski dosya tam olduğu yerde kalır, yenisi `slskd/` altında durur.

Hiçbir şey kaybolmaz, ama kopyalarınız olur. Bir dosyayı gerçekten değiştirmek için yolu, biçimi ve etiketleri koruyan [Sesi değiştir](replace-audio.md) sayfasına bakın.
:::

### Kapak dosyadan değil, Spotify veya YouTube Music’ten gelir

İndirilen sesin taşıdığı her kapak görseli — bir slskd dosyasına gömülü yüksek çözünürlüklü kapak dahil — etiketleme sırasında **atılır ve değiştirilir**. Downtify her zaman parça için Spotify veya YouTube Music’ten getirdiği kapağı, yapılandırdığınız [kapak çözünürlüğünde](#cover-art-resolution) (varsayılan 600 px) gömer. Aynısı başlık, sanatçılar, albüm ve diğer etiketler için de geçerlidir: kaynağın kendi etiketleri korunmaz.

İstediğiniz zaten sahip olduğunuz dosyalarda daha büyük kapaklarsa, yeniden indirmek uzun yoldur. [Kitaplığı iyileştir](library-upgrade.md) tam olarak bunu yapar — her dosyanın gömülü kapağını Spotify, iTunes ve YouTube Music ile karşılaştırır, en büyüğünü yazar, eksik sözleri ve etiketleri doldurur ve sese asla dokunmaz.

Zaten diskte olan bir şarkıyı hiç indirmemek için kapatın. Bu en çok bir çalma listesi indirirken, bir [CSV kitaplığı](library-import.md) içe aktarırken ya da [Çalma Listesi İzleyici](playlist-monitor.md)’nin birbirleriyle veya kitaplığınızdaki şarkılarla parça paylaşan çalma listelerini eşitlemesine izin verirken önemlidir — seçenek açıkken bu kopyaların her biri yeniden indirilir.

Kapalıyken Downtify şarkıyı yalnızca yeni indirmenin gideceği yerde değil, **indirme klasörünün her yerinde** arar:

- kitaplık kökü (tek parça indirmeleri),
- herhangi bir çalma listesinin klasörü (çalma listesi indirmeleri, CSV içe aktarmaları, Çalma Listesi İzleyici),
- bir sanatçı/albüm klasörü veya *Sanatçıya/Albüme göre düzenle*’yi açıp kapatmadan önceki düz düzen.

Bir ses dosyası (`.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`), [çıktı dosya adı şablonunun](#output-filename-template) o şarkı için ürettiği ada sahipse — büyük/küçük harf ayrımı yapılmadan karşılaştırılarak — şarkı zaten indirilmiş sayılır. Geride kalmış tek başına bir `.lrc` söz dosyası sayılmaz. Şablon klasörler içeriyorsa (örn. `{artists}/{title}`), bu klasörlerin de eşleşmesi gerekir; böylece başka bir sanatçının aynı başlıklı şarkısı bununla karıştırılmaz. Dosyalar bir Spotify/YouTube parça kimliği taşımadığı için eşleştirme ada göre yapılır: yeniden adlandırdığınız veya farklı bir dosya adı şablonuyla kaydedilmiş bir dosya tanınmaz.

Bir şarkı atlandığında:

- Hiçbir şey getirilmez: ses, kapak, söz yok, yeniden etiketleme yok. Spotify parçaları için denetim YouTube Music aramasından bile önce çalışır; yani zaten indirilmiş şarkılar hiçbir arama isteğine mal olmaz.
- Kuyruk şarkıyı bitmiş gösterir ve çalma listesi [M3U dosyaları](m3u-export.md) var olan dosyaya, nerede olursa olsun işaret eder (örn. `../Sanatçı - Başlık.mp3`); böylece çalma listesi yine de tam olarak çalar.
- Aynı şarkı aynı anda iki kez kuyruğa alınırsa (bir çalma listesinde iki kez listelenmiş veya paralel indirilen iki çalma listesinde), yalnızca bir kopya indirilir. Diğeri onu bekler ve sonra atlanır.

## Uzun parçalar

**Ayarlar → İndirmeler ve dosyalar → En uzun parça**, hem indirmeler *hem de* akışlar için parça uzunluğunu sınırlar (varsayılan **10 dakika**, `0` her şeyi alır). Daha uzun şarkılar hiçbir şey getirilmeden önce reddedilir; kuyruk hatası *“… üzerindeki parçalar indirilmez”*dir — saatlik miksler ve yüklemeler bir kitaplık parçasının olması gereken şey değildir. Aynı sınır akışı da korur: daha uzun bir parça `400` ile reddedilir (uzunluğunu bilen çağıranlar `duration` verir ve önbellekteki dosya her durumda yoklanır), böylece uzun yüklemeler akış önbelleğinde de birikmez. Zaten indirilmiş dosyalar ve podcast bölümleri (genellikle daha uzundur) etkilenmez.

## Ses sağlayıcı

Varsayılan ses sağlayıcı **YouTube Music**’tir. Downtify, parça süresini karşılaştırarak en iyi eşleşmeyi aramak için [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) kullanır. YouTube Music’te kabul edilebilir bir eşleşme yoksa ya da yalnızca süresi çok farklı olan (muhtemelen başka bir kayıt) varsa, Downtify otomatik olarak standart YouTube aramasına geçer — bkz. [Nasıl çalışır](../how-it-works.md#fallback-to-standard-youtube).

**Ayarlar → Ses kaynakları** ayrıca yalnızca standart **YouTube**’u ya da **slskd**’yi (Soulseek) sıralı bir yedek listesi olarak kullanabilir — bkz. [slskd ve Navidrome](slskd-navidrome.md#audio-sources-and-fallback-order).

### Belirli bir ses kaynağını zorlama

Downtify yanlış YouTube Music videosunu seçerse (örn. orijinal yerine bir cover), parça başına geçersiz kılabilirsiniz:

**Seçenek A — doğrudan bir YouTube Music URL’si yapıştırın**

`https://music.youtube.com/watch?v=…` (veya normal bir `youtube.com/watch?v=…` URL’si) adresini arama çubuğuna yapıştırın ve indire basın. Downtify sesi tam o videodan getirir.

::: info
YouTube URL’si ile indirirken üst veriler (başlık, sanatçı, kapak) Spotify yerine YouTube’dan gelir. Temiz etiketler için Seçenek B’yi kullanın.
:::

**Seçenek B — başarısız bir parçada sesi zorlayın**

1. **İndirme Kuyruğu**’nda, başarısız bir parçanın altındaki **Ses kaynağını zorla**’ya tıklayın.
2. Beliren alana bir YouTube veya YouTube Music URL’si yapıştırın.
3. **Enter**’a basın veya **Uygula**’ya tıklayın.

Downtify parçayı tam o videoyu kullanarak yeniden indirir ve tüm Spotify üst verilerini (başlık, sanatçı, albüm, kapak, söz) korur.

## Gömülü üst veriler

Downtify, biçimden bağımsız olarak indirilen her dosyaya aşağıdaki etiketleri gömer:

| Etiket | Kaynak |
|-----|--------|
| Başlık | Spotify embed |
| Sanatçı(lar) | Spotify embed |
| Albüm | Spotify embed — tek parça indirmesinde, parçanın herkese açık Spotify sayfasının andığı albüm (parçanın embed’inde yoktur) |
| Yıl | Spotify embed (parça düzeyinde getirme) |
| Albüm kapağı | Spotify tarafından çözülen parçalar için Spotify embed (parça düzeyinde kapak); aksi halde YouTube Music küçük resmi veya Deezer kapağı. İsteğe bağlı — bkz. [Kapakları indir](#download-cover-art) ve [Kapak çözünürlüğü](#cover-art-resolution) |
| Söz | lrclib (etkinse) |
