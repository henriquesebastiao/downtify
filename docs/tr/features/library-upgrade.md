---
icon: lucide/wand-sparkles
---

# Kitaplığı iyileştir

Zamanla oluşmuş bir kitaplık, bir parça indirildiğinde her Downtify sürümünün yapabildiğini taşır: bir kaynağın sunduğu en küçük kapak, söz yok, albümü ya da yılı olmayan etiketler. **Kitaplığı iyileştir** diskte zaten olana bakar ve yalnızca geride kalanı onarır — yeniden indirme yok, elle halledilecek bir şey yok.

**Kitaplık → Kitaplığı iyileştir** üzerinden açın.

::: info Varsayılan iyileştirmeler yalnızca etiketleri yeniden yazar
Varsayılan mod **kapakları, sözleri ve etiketleri** yeniden yazar. İsteğe bağlı [Deemix değiştirme](#deemix-recording-replacement) ayrı bir tarama modudur ve varsayılan olarak kapalıdır. Farklı bir sürümü elle seçmek için [Sesi değiştir](replace-audio.md) sayfasını kullanın.
:::

## Nasıl çalışır

1. **Tarama.** Downtify her kitaplık parçasını okur ve geride kalanı kategori başına bildirir. Hiçbir şey yazılmaz.
2. **Seçim.** Taramanın bir şey bulduğu her kategori, parça sayısı ve bir anahtarla listelenir. İstemediğinizin işaretini kaldırın.
3. **İyileştirme.** Seçilen parçalar tek tek işlenen bir kuyruğa girer. Duraklatabilir, sürdürebilir veya durdurabilirsiniz ve yeniden başlatmadan sağ çıkar.

## Neyi onarır

| Kategori | Ne yapar | Nerede arar |
|---|---|---|
| **Kapakları iyileştir** | Hedef boyuttan küçük bir kapağı değiştirir | Spotify, Apple Music (iTunes), YouTube Music |
| **Eksik şarkı sözlerini ekle** | Sözü olmayan parçalar için gömülü olarak ve `.lrc` yan dosyası olarak söz doldurur | [Söz sağlayıcılarınız](lyrics.md), sizin sıranızla |
| **Etiketleri yenile** | Albüm, albüm sanatçısı, yayın tarihi ve parça numarasını doldurur — eski tek parça indirmelerinde eksik olan albüm dahil | Spotify |

Bir parça şu durumlarda geride sayılır:

- gömülü kapağının kısa kenarı **hedef boyuttan küçükse** (hiç kapağı olmayan parça da sayılır);
- **ne** gömülü sözü **ne de** bir `.lrc` yan dosyası varsa (dosyanın yanında ya da Ayarlar’daki söz klasöründe);
- etiketlerinde **albüm**, **albüm sanatçısı**, **yıl** veya **parça numarası**ndan biri eksikse.

**Etiketleri yenile** yalnızca Downtify’ın hâlâ Spotify parça kimliğine sahip olduğu parçalar için çalışır — Spotify bağlantısından indirdikleri, [parça dizininde](library-catalog.md#what-gets-stored) tutulanlar. Diğer parçalar kuyruğa alınır ama _Yapacak bir şey yok_ olarak döner.

## Seçenekler

### Şu boyutun altındaki kapakları iyileştir

`300px` · `500px` · **`600px`** · `1000px` · `1200px`

Bu boyutta veya daha büyük kapaklara dokunulmaz. Downtify yalnızca dosyadakinden **kesinlikle daha büyük** bir kapak yazar; bu yüzden bir iyileştirmeyi iki kez çalıştırmak boşuna hiçbir şeyi yeniden yazmaz.

Boyutlar nereden gelir:

| Kaynak | Tipik boyut |
|---|---|
| **Apple Music (iTunes)** | 1200px ve üzeri |
| **Spotify** | 640px’e kadar |
| **YouTube Music** | [kapak çözünürlüğü](download-settings.md) ayarına kadar, en fazla ~1200px |

Daha önce indirilmiş bir kitaplığın sık sık 300–640px’te takılı kalmasının nedeni de budur: Spotify kapaklarını sabit boyutlarda yayımlar ve sunduğu en büyük 640px’tir.

### Kapak kaynağı

| Seçim | Davranış |
|---|---|
| **Mevcut en yüksek çözünürlük** (varsayılan) | Her kaynağa sorar ve en büyük görüntüyü tutar |
| **Spotify’ı yeğle** / **Apple Music’i yeğle** / **YouTube Music’i yeğle** | Bu kaynakta herhangi bir şey varsa onu kullanır; diğerleri yalnızca onda hiçbir şey olmadığında yedektir |

### Bir parçayı şu süre boyunca yeniden denetleme

`Her parçayı her zaman denetle` · `7 gün` · **`30 gün`** · `90 gün` · `365 gün`

Bir parçaya bakıldıktan sonra sonraki tarama onu bu süre boyunca atlar; böylece büyük bir kitaplık üzerindeki ikinci çalıştırma aynı kaynaklara aynı parçaları yeniden sormaz.

Bellek **parça ve kategori başına** tutulur; kısmi çalıştırmaları çalıştıran da budur: 16.000 parçanın yalnızca kapaklarını onarmak, sözlerine hiç bakılıp bakılmadığı hakkında bir şey söylemez, bu yüzden sonraki bir söz çalıştırması hepsini yine ele alır. Bir tarama ayrıca incelediği ve yapacak bir şey bulmadığı kategorileri de kaydeder — bakıp bir şey bulmamak da diğerleri gibi bir denetimdir.

Downtify her parça ve kategori için şunları hatırlar: ne zaman denetlendiği, onu denetleyen Downtify sürümü ve — kapaklar için — bulunan en büyük kapak ile nereden geldiği. Hangi söz sağlayıcılarına zaten sorulduğu ayrıca, şarkı ve sağlayıcı başına tutulur (bkz. [Şarkı sözleri](lyrics.md)).

İki şey onu her zaman geçersiz kılar:

- **daha yeni bir Downtify sürümü** her şeyi yeniden denetler, çünkü öncekinden daha iyi eşleştirebilir ya da etiketleyebilir;
- **Her parçayı her zaman denetle**’yi seçmek o tarama için belleği yok sayar.

Bir tarama, her şey yakın zamanda denetlendiği _için_ yapacak bir şey bulamazsa bunu söyler ve açıklamasız bir “iyileştirilecek bir şey yok” bırakmak yerine belleksiz yeniden çalıştırmayı önerir.

## Çalışırken

İlerleme paneli kuyruktan biten parçaları, yaklaşık bir veri miktarını (`8.4 GB of 51.3 GB`) ve kaç tanesinin iyileştirildiğini, yapacak bir şeyi olmadığını ya da başarısız olduğunu gösterir. Her parça ne yaptığını gösterir — _Eşleştiriliyor_, _Kapak aranıyor_, _Şarkı sözü aranıyor_, _Dosya yazılıyor_ — ve neyin değiştiğiyle biter, örn. `artwork 1200px (itunes)`.

**Duraklat**, işlemdeki parçadan sonra durur ve kuyruğu korur. **Durdur** geri kalanını bırakır; zaten iyileştirilen parçalar iyileştirilmiş kalır. Sayfadan ayrılabilirsiniz — çalıştırma sürer ve açık diğer sekmeler onu izler.

Kuyruk `/data/downtify_library.db` içinde yaşar; yani çalıştırma ortasında **Downtify’ı (veya kapsayıcıyı) yeniden başlatmak** onu kaldığı yerden sürdürür. İşlem öldüğünde işlemde olan bir parça kuyruğa geri konur.

## Bir iyileştirme başarısız olursa hiçbir şey kaybolmaz

Her yazma, özgün dosyanın yanındaki bir çalışma kopyasına gider (`<ad>.downtify-upgrade.<uzantı>`). Kopya yerine taşınmadan önce aynı uzunlukta ses olarak açılmak zorundadır; aksi halde atılır ve özgün dosyaya dokunulmaz. Bu dosya asla kendi başına bir parça olarak görünmez ve parça bittiği anda gider.

Özgün **değişiklik zamanı korunur**, böylece bir kitaplığı iyileştirmek _Son eklenenler_’i yeniden karıştırmaz.

### Salt okunur müzik klasörleri

Bir iyileştirme etiketleri yerinde yeniden yazar; bu yüzden salt okunur dosya sistemindeki parçalar, üst veri, kapak veya söz aranmadan önce bir açıklamayla **atlanır**. Çalınabilir ve çalma listelerinde kalırlar; dosyaları ve bağlama izinleri değişmez. Atlanan salt okunur bir parça başarıyla denetlenmiş olarak hatırlanmaz, bu yüzden klasörü sonradan yazılabilir olursa yeniden ele alınabilir. Beklenmeyen izin, disk alanı ve G/Ç hataları yine başarısızlık olarak görünür.

Bu, korumalı ses dosyalarını yeniden yazmadan kapakları ve sözleri Downtify’ın veri klasöründe ayrı tutabilen [mevcut klasör zenginleştirmesinden](external-library.md) farklıdır.

## Ses neden değiştirilmez

Sıradan etiket iyileştirmeleri sesi değiştirmez. Aşağıdaki ayrı mod tam kayıt üst verisi ve yayın referansı gerektirir; belirsiz sürümler elle inceleme için kalır.

## Deemix ile kayıt değiştirme

[Deemix kaynağını](deemix.md) etkinleştirip sınadıktan sonra **Kitaplığı iyileştir**, taramadan önce iki bağımsız anahtar sunar:

- **Use verified Deemix recordings**: tercih edilen bir harici koleksiyonun gizlediği kopyalar dahil özgün Downtify indirmelerini tarar. Sanatçıyı, tam başlığı/sürümü ve albümü tam olarak eşleştirir; belirsiz katalog sonuçlarını reddeder. Eski klibin süresi, doğru bir katalog kaydını reddetmek için kullanılmaz. İndirilen etiketleri, katalog süresini, seçilen kaliteyi ve tam FFmpeg çözümlemesini doğrular.
- **Remove old Downtify audio after import**: ek olarak değişmemiş her özgün dosyayı yayımlamadan sonra kaldırır. Varsayılan olarak kapalıdır. Özgünleri tutmak yine de çalma listelerini ve favorileri Deemix kaydına günceller.

Bu tarama, kapak/söz/etiket işleri yerine bir **ses** kategorisi üretir. Çıktı dosyalarına, kapağa, albüm düzenine ve yerel sözlere Deemix sahiptir. Downtify bunları yerinde okur. Mevcut yerel veya gömülü sözler korunur; yalnızca eksik sözler, sesi yeniden yazmadan, yazılabilir özel bir söz klasöründe tamamlanabilir. Deemix MP3 için yapılandırıldığında daha yüksek kaliteli kayıpsız bir özgün dosya korunur.

Yayımlama parti başına bir kez olur. M3U yorumları, elle konulan işaretler ve parça sırası korunur; sonra katalog yolları, çalma listesi üyelikleri, her kullanıcının beğenileri, sahiplik ve gizli parça kuralları tek bir SQLite işleminde taşınır. Eski dosyaların önbellekteki Navidrome kimlikleri yeni bir yerel arama için geçersiz kılınır. Daha önce verilmiş mobil kimlikler ve eski oynatma URL’leri kayıtlı değiştirmeye salt okunur takma adlar tutar; değişiklik işlemleri bu URL takma adlarını asla kullanmaz.

Kitaplık veritabanındaki kalıcı makbuzlar kaynak/hedef SHA-256 değerlerini ve yayımlama durumunu kaydeder. Kaynaklar, değiştirme ve referanslar doğrulanana kadar kalır. Değişmiş ya da eksik bir bağlama, düzenlenmiş bir dosya, harici salt okunur bir çalma listesi referansı, etkin oynatma veya başarısız bir katalog yayımlaması temizliği görünür bir nedenle durdurur. Duraklat/sürdür ve yeniden başlatma makbuzları yeniden kullanır. Genel bir yineleme taraması ya da yaşa dayalı temizlik yoktur: yalnızca Downtify’ın indirme klasöründeki doğrulanmış özgünler uygundur. Elle yapılan Deemix/slskd indirmeleri, harici özgünler, dizinler ve yan dosyalar asla silinmez. Bir özgün kaldırıldıktan sonra kapsayıcıyı geri almak o dosyayı geri getirmez; gerekirse kendi depolama yedeğinizden geri yükleyin.

Bağlama adları Docker yollarından farklı olan NAS kullanıcıları için bir yönetici, `DOWNTIFY_DEEMIX_M3U_ROOT` değerini Deemix köküne çözümlenen bir kapsayıcı takma adına ayarlayabilir. Göreli M3U yolları bu takma adı kullanır (örneğin `/music/existing`’a eşlenen `/Download`). İsteğe bağlı `DOWNTIFY_LIBRARY_READY_MARKERS`, hazırlıktan ve temizlikten önce denetlenen işaretçi yolları ve beklenen metinden oluşan bir JSON nesnesidir. Eksik bir işaretçi güvenli tarafta başarısız olur. Varsayılan mod için değişkenlerin hiçbiri gerekli değildir.

Tarama API’si `replace_audio_deemix: true`, isteğe bağlı `delete_replaced_audio: true` ve sınırlı bir pilot için isteğe bağlı `files: ["relative/original.mp3"]` kabul eder. Bu taramayı başlatmak `categories: ["audio"]` seçer. Çalıştırma durumu, değiştirme sayılarını ve yayımlama duraklatıldığında bir `finalization_error` içerir. Bir Deemix kuyruk öğesi tamamlandı dediği için hiçbir kaynak dosya kaldırılmaz.

### Belirsiz bir kaydı inceleme

Atlanan veya başarısız bir ses işi **Choose a Deezer recording** sunar. Tam bir parça bağlantısı yapıştırın, sanatçısını, albümünü ve süresini önizleyin, sonra **Analyze this choice**’ı seçin. Bu yalnızca yeni bir tek parça taraması hazırlar; değiştirmeyi başlatmak için o taramayı onaylayın. Varsayılan otomatik eşleştirici asla farklı bir albümü tahmin etmez.

Bu açık seçim eski bir albüm etiketini düzeltebilir, ama tam başlık/sürüm ve sanatçı yine de uyuşmalıdır. Bilinen açık içerikli bir özgün dosya sessizce temiz bir sürüm olamaz. Seçilen kayıt aynı süre, kalite, çözümleme, referans ve silme denetimlerinden geçer. Farklı bir seçim, önceden hazırlanmış bir makbuzu sessizce yeniden kullanamaz. Gelişmiş tarama yükü seçimi `deemix_recordings: {"relative/original.mp3": "123456"}` olarak kaydeder; o dosyayla sınırlıdır ve yeniden başlatma/sürdürme için saklanır.

## API

| Yöntem | Yol | Açıklama |
|---|---|---|
| `GET` | `/api/library/upgrade` | Çalıştırma durumu, kuyruk sayıları ve taramanın bulduğu |
| `GET` | `/api/library/upgrade/jobs` | Parça başına satırlar (`status`, `stage`, `detail`) |
| `POST` | `/api/library/upgrade/scan` | Kitaplığı tarar; hiçbir şey yazmaz |
| `POST` | `/api/library/upgrade/start` | Seçilen `categories` için çalıştırmayı başlatır |
| `POST` | `/api/library/upgrade/pause` | Geçerli parçadan sonra durur, kuyruğu korur |
| `POST` | `/api/library/upgrade/resume` | Duraklatılmış bir çalıştırmayı sürdürür |
| `POST` | `/api/library/upgrade/cancel` | Kuyruğun geri kalanını bırakır |

İlerleme ayrıca [WebSocket](../api-reference.md#websocket) üzerinden `{"type": "library_upgrade", "upgrade": {…}}` olarak itilir.

İstek ve yanıt biçimleri için [API başvurusuna](../api-reference.md#library) bakın.
