---
icon: lucide/eye
---

# Çalma Listesi İzleyici

Çalma Listesi İzleyici, favori Spotify, herkese açık Deezer ve YouTube Music çalma listelerinizi — ve takip ettiğiniz sanatçıları — izler ve yeni parçaları ile yeni yayınları ortaya çıktıkça kendiliğinden, elinizi sürmeden indirir.

İki tür izleme vardır; her biri İzleyici sayfasının kendi sekmesindedir (**Çalma listeleri** ve **Sanatçılar**, `/monitor/playlists` ve `/monitor/artists` adreslerinde):

| İzleme | Yapıştırın | İndirir |
|-------|-------|-----------|
| **Çalma listesi** | Bir Spotify, herkese açık Deezer veya YouTube Music çalma listesi URL’si | Çalma listesindeki her parçayı, sonra sonradan eklenen her parçayı |
| **Sanatçı** | Bir Spotify **sanatçı** URL’si veya bir YouTube Music sanatçı URL’si | Sanatçının tüm diskografisini, sonra her yeni yayını |

Her izleme adının altında izlediği bağlantıyı ve eklendiği hizmeti belirten bir **Spotify**, **Deezer** ya da **YouTube Music** rozetini gösterir.

Sanatçı izlemelerinin nasıl çalıştığı için bkz. [Sanatçı İzleme](#artist-watch).

İzlemeler onları oluşturana aittir: her hesap kendi çalma listelerini ve sanatçılarını izler (aynı URL iki kez izlenirse iki kez taranır) ve bir tarama indirmelerini izlemenin sahibine atfeder. Bir yönetici tüm izlemeleri görür.

## Nasıl çalışır

Downtify, 60 saniyede bir çalışan bir arka plan görevi tutar. Her taramada, etkin her izlemenin (yapılandırılmış aralığına göre) denetlenme zamanının gelip gelmediğine bakar. Bir *çalma listesinin* zamanı geldiğinde Downtify:

1. Spotify, Deezer veya YouTube Music’ten tam parça listesini getirir
2. Onu zaten indirilmiş parçalar kümesiyle karşılaştırır
3. Yeni parçaları elle indirmeyle aynı işlem hattıyla indirir
4. Çalma listesinin M3U dosyasını günceller (M3U üretimi etkinse)

İzlemeyi eklediğiniz anda başlayan ilk denetim, çalma listesinde zaten olan her şeyi indirir; sonraki denetimler yalnızca o zamandan beri eklenenleri indirir. “Zaten indirilmiş” olan, indirme klasörüne bakılarak değil, küçük bir SQLite veritabanında (`/data` altındaki `downtify_monitor.db`) izlenir — bu yüzden indirilen bir dosyayı diskte başka bir yere (kendi kitaplık düzeninize, başka bir sürücüye, nereye olursa) taşımak, Downtify’ın onun eksik olduğunu düşünüp sonraki denetimde yeniden indirmesine **neden olmaz**.

Ayrı bir tarama her saat çalışır ve indirilmiş her parçanın dosyasının hâlâ orada olup olmadığına bakar. Gerçekten silinen dosyalar (taşınanların aksine) o anda unutulur; böylece parça yeniden indirilmeye uygun hale gelir — anında değil, o saatlik taramadan sonraki izleme denetiminde.

Bir izleme asla aynı anda iki kez denetlenmez. Bir izleme eklemek ilk denetimini hemen başlatır; sonraki zamanlanmış tarama geldiğinde o denetim hâlâ indiriyorsa, tarama aynı parçaların ikinci ve çakışan bir indirmesini başlatmak yerine izlemeyi atlar.

## Çalma listesi ekleme

1. Kenar çubuğundan **İzleyici**’yi açın (telefonda: **Daha fazla → İzleyici**) ve **Çalma listeleri** sekmesinde kalın
2. Bir çalma listesi URL’si yapıştırın:
    - Spotify: `https://open.spotify.com/playlist/…`
    - Herkese açık Deezer çalma listesi: `https://www.deezer.com/playlist/…` (dil önekli bağlantılar da çalışır)
    - YouTube Music: `https://music.youtube.com/playlist?list=…` (bir `www.youtube.com/playlist?list=…` bağlantısı da çalışır)
3. Bir denetim aralığı seçin (15 dakikadan ayda bire kadar)
4. **Çalma listesini izle**’ye tıklayın

Her sekmenin kendi kutusu vardır. Çalma listeleri sekmesine bir sanatçı bağlantısı (veya Sanatçılar’a bir çalma listesi bağlantısı) yapıştırmak hiçbir şey eklemez: sayfa bunun ne tür bir bağlantı olduğunu söyler ve doğru sekmeye taşımayı önerir.

İzlemeyi bir çalma listesinin sayfasından da başlatabilirsiniz: bağlantısını arama çubuğuna yapıştırın ve **Yeni parçaları izle**’yi (veya bir YouTube Music sanatçısında **Yeni yayınları izle**’yi) kullanın. Kitaplıktaki indirilmiş çalma listeleri aynı eylemi **⋯** menülerinde sunar. Bu şekilde eklenen izlemeler 6 saatlik aralık kullanır — onu İzleyici sayfasında değiştirin.

## Deezer çalma listeleri

Herkese açık Deezer çalma listeleri diğerleri gibi izlenir: bağlantıyı **Çalma listeleri** sekmesine yapıştırın, çalma listesinin sayfasında **Yeni parçaları izle**’yi kullanın ya da [Müzik listeleri](charts.md) sayfasındaki bir çalma listesi kartının **⋯** menüsünden **Yeni parçaları izle**’yi seçin. Deezer hesabı gerekmez ve çalma listesi ne kadar uzun olursa olsun her parça getirilir. Şarkılar diğer Deezer bağlantıları gibi [ses kaynaklarınızdan](download-settings.md) indirilir; çalma listesi de bir Spotify listesi gibi M3U dosyasını, kapak görselini ve Kitaplık’taki yerini alır — M3U dosyaları kapalıyken bile Kitaplık hangi şarkıların ona ait olduğunu bilir. Yalnızca herkese açık çalma listeleri izlenebilir; bir Deezer **sanatçı** bağlantısı indirilebilir ama izlenemez.

## YouTube Music çalma listeleri

Spotify’da olmayan şarkılar için bir YouTube Music çalma listesi kullanın: remiksler, canlı setler, cover’lar, tanıtım kanallarının yüklemeleri. Her parça **çalma listesindeki tam o videodan** indirilir. Downtify onu yeniden aramaz; yani eline geçen, çalma listesine eklediğindir.

- **Tüm parçalar getirilir**, çalma listesi ne kadar uzun olursa olsun. Silinmiş veya özel videolar atlanır.
- **YouTube Music’in grileştirdiği şarkılar yine de indirilir.** Dönüştürücüler ve içe aktarıcılar (Soundiiz, TuneMyMusic ve benzerleri) tarafından yapılan çalma listeleri, şarkıları çoğunlukla YouTube Music’in kullanılamaz gösterdiği ve şarkı kimliği vermediği düz YouTube yüklemeleri olarak listeler. Downtify videoyu girdinin küçük resminden bulur ve diğerleri gibi indirir; böylece böyle bir çalma listesi boş çıkmaz. Gerçekten silinmiş veya özel yapılmış bir video indirilemez: YouTube Music onu öyle işaretlediğinde atlanır, yalnızca küçük resim verdiğinde parça kuyrukta başarısız görünür.
- **Sanatçı ve başlık video başlığından gelir.** Birçok çalma listesi girdisi, onları yayımlayan kanala atfedilmiş yüklemelerdir (örn. `MrSuicideSheep`) ve gerçek katkı `Bronze Whale - Patterns` gibi başlıktadır. Katalog yayını olmayan her şey için Downtify `Sanatçı - Başlık`’ı dosya adına ve etiketlere böler. Ayrıca `(Official Video)` veya `[Lyrics]` gibi sonekleri atar. Tireden sonraki bir sürümü adlandıran kısım (`Yellow - Live at Glastonbury`) başlıkta kalır. Katalog parçaları (resmi ses ya da bir albüm altında dosyalanmış her şey) YouTube Music’in kendi sanatçı ve başlığını korur.
- **Her `list=` bağlantısı bir çalma listesi değildir.** Bir albümün `OLAK5uy_…` bağlantısı yine albüm olarak indirilir. Bir `watch?v=…&list=…` bağlantısı çalmakta olan tek şarkıdır. Bir radyo karışımının (`list=RD…`) sabit parça listesi yoktur ve izlenemez.

## Sanatçı İzleme

Sanatçı başına bir çalma listesi oluşturmak yerine bir sanatçı bağlantısı yapıştırın; Downtify onun tüm kataloğunu izler. İzleyici sayfasının **Sanatçılar** sekmesinden bir tane ekleyin — URL’yi yapıştırın, bir aralık seçin, **Sanatçıyı izle**’ye tıklayın. Sanatçı izlemeleri parça sayısı yerine yayın sayısı gösterir.

Kabul edilen URL’ler:

- Bir Spotify sanatçı URL’si (`https://open.spotify.com/artist/…`)
- Kanal ile (`https://music.youtube.com/channel/UC…`) veya handle ile (`https://music.youtube.com/@HenriqueeJuliano`) bir YouTube Music sanatçı URL’si

Bir handle, izlemeyi eklediğinizde sanatçının kanalına çözümlenir; böylece handle ile ve kanal URL’si ile yapıştırılan aynı sanatçı tek bir izleme olarak tanınır. Bir YouTube Music sanatçısına ait olmayan bir handle reddedilir.

Her taramada Downtify sanatçının diskografisini listeler, zaten işlediği yayınlarla karşılaştırır ve yeni olan her şeyin her parçasını indirir. Kararlı durumdaki bir tarama tek bir isteğe mal olur — parça listeleri yalnızca daha önce görmediği yayınlar için getirilir.

::: info Diskografi neden YouTube Music’ten gelir
Spotify’ın herkese açık embed’i bir sanatçının adını ve en çok dinlenen parçalarının önizlemesini gösterir, ama diskografisini **göstermez** — onu okumak, Downtify’ın bilerek kullanmadığı Spotify API kimlik bilgileri gerektirir. Bu yüzden bir Spotify sanatçı bağlantısı adına çözümlenir ve YouTube Music’teki aynı sanatçıyla eşleştirilir; ses de oradan getirilir. Artısı: Downtify’ın görebildiği her yayın gerçekten indirebildiği bir yayındır. Dengesi: bağlantı, tam olarak bu ada sahip YouTube Music sanatçısını izler (büyük/küçük harf ve noktalama dikkate alınmaz); birden fazla sanatçı bu adı taşıyorsa YouTube Music’in en iyi eşleşmesini. Yaygın bir adda izlemenin kastettiğiniz sanatçı olduğunu denetleyin, değilse YouTube Music sanatçı URL’sini doğrudan yapıştırın. Tam adını hiçbir YouTube Music sanatçısının taşımadığı bir Spotify sanatçısı yalnızca bu şekilde eklenebilir: Downtify tahmin yürütmez.
:::

::: warning İlk tarama tüm eski kataloğu indirir
Bir sanatçı eklemek onun **her** yayınını kuyruğa alır; üretken bir sanatçı için bu yüzlerce albüm ve single olabilir. Bir grup sanatçı eklemeden önce **[İndirmeler arası bekleme](download-settings.md#delay-between-downloads)**’yi ayarlayın, yoksa büyük olasılıkla hız sınırına takılırsınız — ya da eski kataloğu tümüyle atlamak için **Yalnızca yeni yayınlar**’ı (aşağıda) açın.
:::

### Neyin indirileceğini seçme

**Sanatçılar** sekmesindeki bağlantı kutusunun altında (ve bir izlemenin **Düzenle** penceresinde) iki seçenek bir sanatçı izlemesinin neyi indireceğine karar verir:

| Seçenek | Ne yapar |
|--------|--------------|
| **İndir: Albümler / Single’lar / EP’ler** | Yalnızca işaretli türlerin yayınları indirilir. Üçü de varsayılan olarak açıktır; en az biri açık kalmalıdır. Tür, YouTube Music’in her yayın için kendi etiketidir — etiketlemediği bir yayın albüm sayılır. |
| **Yalnızca yeni yayınlar** | İzleme başladığında sanatçının zaten yayımlamış olduğu her şey atlanır; yalnızca ondan sonra çıkan indirilir. Varsayılan olarak kapalıdır. |

Daha sonra değiştirdiğinizde nasıl davranırlar:

- **Bir türü açmak**, o türün yayınlarını izlemenin bir sonraki denetiminde indirir — **Yalnızca yeni yayınlar** açık değilse eski kataloğu da (o zaman yalnızca izleme başladığından ya da seçenek açıldığından beri çıkanlar). Kapalı bir türün yayınları asla kaydedilmez; yani bir türü bir süre kapatmakla hiçbir şey kaybolmaz.
- Var olan bir izlemede **Yalnızca yeni yayınlar**’ı açmak, o noktada çıkmış her şeyi atlanmış olarak kaydeder; zaten indirilmiş yayınlar olduğu gibi kalır.
- **Kapatmak**, atladığı yayınları (işaretli türlerden) sonraki denetimde indirir.
- **Düzenle** penceresinde seçeneklerden birini kaydetmek, bir sonraki zamanlanmış denetimi beklemek yerine izlemeyi hemen denetler.

Var olan yayınları “atlamak”, sanatçının diskografisine bir kez başarılı bakmayı gerektirir: YouTube Music boş bir liste dönerse (ki bu, hiçbir şey çıkarmamış bir sanatçıdan çok bir aksaklıktır), hiçbir şey kaydedilmez ve sonraki denetim yeniden dener; böylece kötü bir yanıt eski kataloğun sonradan indirilmesine asla yol açamaz. Bir **Yalnızca yeni yayınlar** izlemesini başka bir sanatçıya yöneltmek, o sanatçının eski kataloğunu aynı şekilde atlar.

İzleyici listesi, varsayılan olmadıklarında bir izlemenin süzgeçlerini bağlantısının altında gösterir (örn. **Albümler** · **Yalnızca yeni**).

Bir yayın yalnızca her parçası hesaba katıldığında işlenmiş olarak kaydedilir; bu yüzden geçici bir hatada başarısız olan bir parça sonsuza dek atlanmak yerine sonraki taramada yeniden denenir. Zaten indirilmiş parçalar asla iki kez getirilmez.

Sanatçı izlemeleri M3U dosyası üretmez — parçalar bir çalma listesi olarak değil, [dosya düzeni](file-organization.md) ayarlarınıza göre yerleştirilir.

### Önerilen sanatçılar

Sanatçı izlemeleri listesinin altında, **Sanatçılar** sekmesi takip edilecek sanatçıları iki listede önerir:

| Liste | Kimler var |
|-------|------------|
| **Dinlediklerine göre** | En çok dinlediğiniz sanatçılar: [Keşfet](discover.md)’in saydığı kendi dinlemeleriniz. Yakın zamandaki dinlemeler daha çok sayılır: bir dinlemenin ağırlığı her 45 günde yarıya iner; bu yüzden geçen yıl çok dinlediğiniz bir sanatçı, şu sıralar her gün dinlediğiniz bir sanatçının altında kalır. |
| **Kitaplığına göre** | Gördüğünüz kitaplıkta en çok parçası, ardından albümü olan sanatçılar. |

Zaten izlediğiniz sanatçılar (duraklatılmış izlemeler dahil) ve **Various Artists** gibi derleme adları dışarıda kalır. Her liste aynı anda 20 sanatçı gösterir; **Daha fazla göster** sonrakileri yükler. Listeler yalnızca sizindir, yönetici için de: başka bir hesabın dinlemeleri asla görünmez. Bir yöneticinin kullanıcılardan gizlediği bir sanatçı, Kitaplık’ta olduğu gibi kullanıcının listelerinde de yer almaz.

Listeleri yüklemek hiçbir şey aramaz. **Takip et**, adı bir sanatçı izlemesinin sanatçıyı takip ettiği yer olan YouTube Music’te arar:

- orada tam olarak tek bir sanatçı bu adı taşıyorsa, izleme yukarıdaki kutuda ayarlanan aralık ve **İndir** / **Yalnızca yeni yayınlar** seçenekleriyle hemen eklenir;
- aksi halde (adaşlar varsa ya da hiçbir sanatçı tam olarak bu adı taşımıyorsa) bir pencere, bulunan YouTube Music sanatçılarını her birinin fotoğrafı ve profil bağlantısıyla gösterir. **Bu sanatçıyı takip et** ile birini seçin ya da sanatçının bağlantısını yukarıdaki kutuya kendiniz yapıştırmak için **Bağlantı yapıştır**’ı kullanın.

Öneriler yalnızca hangi sanatçının izleneceğini seçer: şarkılar her zamanki gibi [ses kaynaklarınızdan](download-settings.md) indirilir.

### Kitaplıktaki sanatçı sayfasından

Kitaplıkta bir sanatçının sayfasında (`/library/artist`) bir **Sanatçıyı izle** düğmesi vardır; böylece zaten sahip olduğunuz bir sanatçıyı bağlantısını aramadan takip edebilirsiniz. Adı, yukarıdaki **Takip et** ile aynı şekilde YouTube Music’te arar:

- orada tam olarak tek bir sanatçı bu adı taşıyorsa izleme hemen eklenir. Her gün denetlenir ve kitaplıkta sanatçının önceki müzikleri zaten bulunduğundan **Yalnızca yeni yayınlar** açıktır;
- aksi halde (adaşlar varsa, hiçbir sanatçı tam olarak bu adı taşımıyorsa ya da arama başarısız olduysa) bir pencere, bulunan YouTube Music sanatçılarını her birinin fotoğrafı ve profil bağlantısıyla, bir Spotify veya YouTube Music sanatçı bağlantısı kutusuyla birlikte gösterir. Üstteki **İndir** ve **Yalnızca yeni yayınlar** seçenekleri takip ettiğiniz sanatçıya uygulanır.

Sunucu izlemeyi ekledikten sonra düğme, aralığı ve seçenekleri değiştirebileceğiniz **İzleyici**’ye giden bir bağlantıya dönüşür; bir ret (örneğin sanatçı zaten izleniyorsa) pencerede gösterilir. Düğme [yalnızca kitaplık modunda](library-only.md) ve **Various Artists** sayfasında gösterilmez.

## Denetim aralıkları

| Etiket | Dakika | En uygun |
|-------|---------|----------|
| Her 15 dk | 15 | Sık güncellenen çalma listeleri |
| Her 30 dk | 30 | |
| Her saat | 60 (varsayılan) | Çoğu çalma listesi |
| Her 3 saat | 180 | |
| Her 6 saat | 360 | |
| Her 12 saat | 720 | |
| Her gün | 1 440 | Yavaş değişen çalma listeleri |
| Her hafta | 10 080 | Haftalık güncellenen çalma listeleri |
| Her 2 haftada | 20 160 | |
| Her ay | 43 200 | Arşiv veya nadiren güncellenen çalma listeleri |

Var olan bir çalma listesinin aralığını, kaldırıp yeniden eklemeden, izleyici kartından istediğiniz zaman değiştirebilirsiniz.

## İzlenen çalma listelerini yönetme

Her sekme yalnızca kendi izleme türünü listeler. Listenin üstünde:

- **Süz** — listeyi daraltmak için bir adın veya bağlantının (örn. bir çalma listesi kimliğinin) bir kısmını yazın
- **Tümü / Duraklatılmış** — yalnızca duraklatılmış izlemeleri göster
- **Tümünü şimdi kontrol et** — geçerli sekmedeki her etkin izlemeyi denetle
- Seçilen dönemde (**7 gün**, **30 gün** ya da **90 gün**) kaç şarkı geldiğini ve tüm izlemeler için toplamda kaç şarkı tuttuklarını, bunların kapladığı alanı (**Diskte**) ve kaçının **Birden fazla izlemede** olduğunu gösteren bir şerit — bkz. [İzleme başına etkinlik ve depolama](#activity-and-storage-per-watch)

Her satırda:

- **Etkin** anahtarı — izlemeyi kaldırmadan duraklat veya sürdür
- **Denetimler** — ne sıklıkta denetlendiği
- **Şimdi kontrol et** (↻) — zamanlamanın dışında hemen denetle
- **Etkinlik** — seçilen dönemdeki yeni şarkılar, haftalık ortalama ve bu hızın artıp azaldığı; tıklayınca izlemenin kendi sayfası açılır
- **Depolama** — yalnızca bu izlemenin tuttuğu şarkıların kapladığı alan, artı diğer izlemelerle kaç şarkıyı paylaştığı
- **Düzenle** (✎) — izlemenin bağlantısını, aralığını ve etkin durumunu gör ve değiştir (bkz. [Bir izlemeyi düzenleme](#editing-a-watch))
- **⋯** — **Etkinlik ve şarkılar** (izlemenin kendi sayfası), duraklat/sürdür, bağlantıyı kopyala, orijinali aç veya **İzlemeyi bırak** (kayıt silinir; indirilen dosyalar korunur)

**Etkinlik** ve **Depolama** diğerleri gibi birer sütundur: **Sütunlar** menüsünden gizleyebilir ya da genişliklerini değiştirebilirsin.

### Bir izlemeyi düzenleme

Bir izlemenin adına ya da **Düzenle** düğmesine tıklayın. Pencere, izlenen tam bağlantıyı **Bağlantıyı kopyala** ve **Orijinali aç** ile birlikte gösterir; ayrıca izlemenin ne zaman eklendiğini, en son ne zaman denetlendiğini ve kaç parça ya da yayını olduğunu. Şunları değiştirebilirsiniz:

- **Bağlantı** — aynı türde bir bağlantı olmalı (çalma listesi izlemesi için bir çalma listesi, sanatçı izlemesi için bir sanatçı):
    - **Aynı** çalma listesine veya sanatçıya başka bir bağlantı (örneğin farklı bir `?si=` paylaşım koduyla ya da `www.youtube.com` yerine YouTube Music bağlantısı) yalnızca saklanan adresi günceller. Başka hiçbir şey değişmez.
    - **Farklı** bir çalma listesine ya da sanatçıya bağlantı, izlemeyi ona yöneltir. İzleme aralığını ve etkin durumunu korur, ama yeni adı alır ve baştan başlar: indirme veya yayın geçmişi temizlenir ve etkinse hemen denetlenir. Kitaplığınızda zaten olan parçalar yeniden indirilmez ve önceki hedefin dosyaları olduğu yerde kalır.
    - Zaten izlenen bir şeye bağlantı reddedilir.
- **Şu aralıkla kontrol et** ve **Etkin**.

Bu, değiştirilen “canlı” çalma listeleri için kullanışlıdır: gerçekte hangi çalma listesini izlediğini görmek için izlemeyi açın ve değiştiyse yenisini yapıştırın.

## Sıralama

Listenin üstündeki **Sırala** denetimi geçerli sekmeyi şuna göre sıralar:

| Alan | Notlar |
|-------|-------|
| Eklenme tarihi | Varsayılan — en yeni önce |
| Ad | Alfabetik |
| Son kontrol | En son denetlenen önce; hiç denetlenmeyenler en son |
| Kontrol sıklığı | En seyrek (en uzun aralık) önce |
| Parça / yayın sayısı | En çok önce |
| Son etkinlik | Seçilen dönemdeki yeni şarkılar |
| Ortalama hız | Dönem içinde günde yeni şarkı |
| Depolama artışı | Dönemin yeni şarkılarının kapladığı alan |
| Kendine ait depolama | Başka hiçbir izlemenin tutmadığı şarkıların alanı |
| İndirilen şarkılar | İzlemenin kendisinin indirdiği, diskteki şarkılar |

Yanındaki düğme artan ve azalan sıra arasında geçiş yapar. Seçim tarayıcıda hatırlanır ve yalnızca listeyi değiştirir — denetim sırasını ya da zamanlamayı değil.

## Günlük eşitleme saati seçme

Varsayılan olarak her gün (veya hafta / 2 hafta / ay) denetlenen bir çalma listesi, aslen eklendiği ya da en son denetlendiği saatte eşitlenir — garanti edilmiş bir gün saati yoktur. Bir gün ve daha uzun eşitlemeleri belirli bir saate sabitlemek için (örn. herhangi bir zaman yerine gece saat 3’te çalıştırmak), `DOWNTIFY_MONITOR_SYNC_TIME` ortam değişkenini `TZ` ile birlikte ayarlayın. Tam başvuru için bkz. [Ortam değişkenleri](../getting-started/environment-variables.md#playlist-monitor).

- Yalnızca tam bir gün veya daha uzun aralıkları etkiler — daha kısa aralıklar (15 dk – 12 sa) etkilenmez; çünkü onları tek bir günlük saate sabitlemek ritimlerini bozar.
- Bir çalma listesi eklendikten sonraki ilk denetim, bu ayardan bağımsız olarak her zaman hemen çalışır.

## Parça başına üst veri zenginleştirme

Spotify çalma listesi embed girdilerinde yayın yılı yoktur ve parça başına albüm kapağı yerine çalma listesi kapağı kullanılır. Downtify, doğru kapağı ve yılı almak için indirmeden önce her yeni parçayı ayrı ayrı yeniden getirir — parça başına getirme başarısız olursa çalma listesi düzeyindeki verilere döner. YouTube Music çalma listesi girdileri bu adımı atlar: her biri zaten kendi videosunun üst verisini taşır.

## M3U entegrasyonu

Çalma listesinin M3U’su **her parça bittikten sonra** yeniden yazılır; yani her şey bittiğinde bir anda ortaya çıkmak yerine tarama indirirken büyür. Çalma listesi ilk parçadan itibaren çalınabilir ve listenin daha aşağısındaki yavaş ya da takılmış bir indirme, zaten gelmiş parçaları asla tutmaz. Taramanın sonundaki son bir yeniden yazma her şeyi dosya sistemine karşı yeniden çözümler.

Elle çalma listesi/albüm indirmeleri ve CSV içe aktarmaları da aynı şekilde davranır. Ayrıntılar için bkz. [M3U dışa aktarma](m3u-export.md#when-it-is-written).

[Çalma listesi kapağını kaydet](playlist-cover-art.md) açıkken kapak, indirilecek parçası olan tarama başına bir kez getirilir — ilk parçadan önce; böylece klasör dolarken çalma listesine benzer. Yeni bir şey bulmayan tarama onu yeniden getirmez.

## Bir çalma listesinden ayrılan şarkılara ne olur

Canlı çalma listeleri (Spotify’ın *Top 50*’si, *Haftalık Keşif*, editoryal listeler) her hafta değişir. Downtify bir izlemeyi **yeni müzik kaynağı** olarak ele alır, asla ne tuttuğunuzu belirleyen bir şey olarak değil:

- **İndirilmiş ses dosyaları bir izleme tarafından asla silinmez.** Bir parça çalma listesinden ayrıldığında da, izlediğiniz her çalma listesinden ayrıldığında da, çalma listesinin kendisi küçüldüğünde de, **İzlemeyi bırak**’a bastığınızda da değil.
- **Çalma listesini yalnızca çalma listesi izler.** Her taramada [M3U dosyası](m3u-export.md), çalma listesinin geçerli parçalarından, geçerli sırasıyla yeniden yazılır; yani düşen bir parça M3U’dan kaybolur. Dosyası klasörde ve kitaplığınızda kalır, aranabilir ve çalınabilir — Navidrome, Jellyfin ya da aynı klasöre yönlendirilmiş her şey üzerinden de.
- **Hiçbir çalma listesinde olmayan bir parça yine de bir parçadır.** Hiçbir şey “yetim” dosyalar için tarama yapmaz.

Bu, bir liste çalma listesini kullanışlı bir keşif akışı yapar: yeni şarkılar kendiliğinden gelir ve geride bıraktıkları kitaplığınız olarak birikir.

```
Top 50 - USA        →  new song appears   →  Downtify downloads it
                    →  song drops out     →  M3U updated, file kept
```

Sesi silen tek şeyler sizin açıkça istedikleriniz: Kitaplıkta bir parça ya da seçim üzerinde **Sil**, Kitaplıktan bir çalma listesini silmek (parçalarını gerçekten siler — önce sorar) veya dosyaları kendiniz dosya sisteminden kaldırmak.

İstemediğin bir şarkıyı listeden çıkarmak ve her kontrolde dışarıda tutmak için onu gizle: bkz. [Listeden gizlenen şarkılar](hidden-playlist-songs.md). Dosyası kitaplığında kalır.

::: info Bir izlemeyi silmek ve bir çalma listesini silmek
**İzlemeyi bırak** (izlemenin ⋯ menüsünde) yalnızca izlemeyi unutur: diskte hiçbir şey değişmez. **Kitaplık** sayfasında bir çalma listesinde **Sil** yıkıcı olandır — o çalma listesinin parçalarını, M3U’sunu ve katalog girdisini kaldırır.
:::

Bir dosya gerçekten kaybolursa — indirme klasöründen çıkardınız ya da elle sildiniz —, saatlik bir tarama bunu fark eder ve Downtify’ın onunla ilgili kaydını unutur; böylece parçayı hâlâ listeleyen bir izlemenin sonraki denetimi onu yeniden indirir. İndirme klasörü içinde yalnızca *taşınan* bir dosya hâlâ bulunur ve yeniden indirilmez.

## Depolama

İzleyici durumu `/data/downtify_monitor.db` konumundaki bir SQLite veritabanında saklanır. Veritabanı şunları kaydeder:

- Her izleme (tür, Spotify veya YouTube Music çalma listesi kimliği ya da YouTube Music kanal kimliği, ad, URL, aralık, etkin durumu, son denetim zamanı). Bir izlemenin Spotify mı YouTube Music mi olduğu saklanan URL’sinden okunur, bu yüzden ek bir sütun gerekmez.
- İzleme başına başarıyla indirilen her parça, diskteki dosya adı dahil
- Sanatçı izlemeleri için, işlenmiş yayınlar; böylece bir tarama yalnızca gerçekten yeni olanların parça listelerini getirir — **Yalnızca yeni yayınlar**ın atladıkları dahil, kapatmanın onları geri getirebilmesi için öyle işaretlenmiş olarak — ayrıca izlemenin yayın türleri ve yalnızca-yeni-yayınlar olup olmadığı
- Bir izlemenin eklediği her parça (`watch_events`): ne zaman, dosya, hangi ses sağlayıcısının getirdiği, izlemenin onu indirip indirmediği ya da kitaplıkta zaten bulup bulmadığı ve ilk kontrolüyle gelip gelmediği. Bu satırlar izlemenin kimliğini, adını ve sahibini o anki hâliyle saklar ve izlemeden uzun yaşar: bir izlemeyi bırakmak ya da başka bir hedefe yöneltmek onları silmez, böylece şarkıları nereden geldiklerini söylemeye devam eder
- Her izlemenin indirmekte başarısız olmaya devam ettiği parçalar (`watch_failures`); biri başarılı olana, listeden çıkana ya da izleme başka bir hedefe yöneltilene kadar

Sanatçı İzleme’den önce oluşturulan veritabanları başlangıçta otomatik taşınır; mevcut satırlar çalma listesi izlemeleri olarak çalışmaya devam eder. Downtify yukarıdaki geçmişi tutmaya başlamadan önce kaydedilen parçalar, ilk açılışta bir kez bilinmeyen sonuçla (**Kayıttan önce**) eklenir — bir izlemenin ilk gününden olanlar onun ilk kontrolü sayılır.

## İzleme başına etkinlik ve depolama

İzleyici sayfası ve her izlemenin kendi sayfası (bir izlemenin **⋯** menüsündeki **Etkinlik ve şarkılar** ya da **Etkinlik** sütununa tıklama) kitaplığını hangi izlemelerin büyüttüğünü gösterir — çok sayıda izlemede ya da otomatik oluşturulan bir mix’in neden beklemediğin şarkılar getirdiğini anlamak için kullanışlıdır.

**Etkinlik olarak sayılanlar.** Yalnızca bir izlemenin gerçekten eklediği şarkılar sayılır: indirdikleri. Kitaplığında zaten bulduğu şarkılar (başka bir izleme ya da kendi indirmen onlara sahipti) ayrıca **Zaten kitaplıkta** olarak sayılır; ilk kontrolün getirdikleri de öyle, çünkü o kontrol listede zaten olan her şeyi indirir. Böylece ilk kontrolü 300 şarkı indirmiş olsa bile durağan bir liste sakin görünür, haftada 15 şarkı ekleyen bir mix de haftada 15 olarak görünür. Downtify bu geçmişi tutmadan önce kaydedilen parçalar eklenmiş sayılır ve sayfa kaç tane olduğunu söyler.

Seçilen dönemde (7, 30 ya da 90 gün, tarayıcıda hatırlanır) bir izleme şunları gösterir:

| Sayı | Ne olduğu |
|--------|------------|
| Yeni şarkılar | Dönem içinde eklediği şarkılar |
| Günde / Haftada / Ayda | Dönem boyunca ortalama hız — ya da izleme daha yeni başladıysa o zamandan beri |
| Eğilim | Günlük (7 gün) ya da haftalık (30 ve 90 gün) yeni şarkılara göre hızın arttığı (**Son zamanlarda daha çok ekliyor**), azaldığı (**Son zamanlarda daha az ekliyor**) ya da sabit kaldığı; karşılaştırılacak üçten az dilim varken **Söylemek için çok yeni** |
| Depolama artışı | Dönemin hâlâ diskte olan yeni şarkılarının kapladığı alan |

**Depolama.** Bir dosya, kaç izlemede olursa olsun bir kez saklanır ve sayılar bunu yansıtır: **Yalnızca bu izlemede** başka hiçbir izlemenin tutmadığı şarkıların alanıdır (izlemeyi bırakıp şarkılarını silmenin boşaltacağı alan), **Ortak** diğer izlemelerin de tuttuğu şarkılardır, İzleyici sayfasındaki şerit de her dosyayı bir kez sayar. Diğer hesapların izlemeleri, bir dosyanın ortak olup olmadığına karar verirken sayılır ama adları gösterilmez.

Bir izlemenin sayfası ayrıca şunları gösterir:

- **Diskteki şarkılar**, **Kendisi indirdi**, **Zaten kitaplıkta** ve **Başarısız** — şarkılarının oraya nasıl geldiği ve kaçının indirilemeye devam ettiği (aşağıda, deneme sayısı ve son hatayla listelenir)
- **Sesin geldiği yer** — diskteki şarkı başına YouTube Music, YouTube, Soulseek (slskd) ya da Deemix
- **Bu izlemeden gelen şarkılar** — tuttuğu her şarkı, en yeniler önce, o zamandan beri listeden çıkanlar dahil, filtrelerle (**Son 30 gün** — ya da seçilen dönem —, **Kendisi indirdi**, **Zaten kitaplıkta**, **Kayıttan önce**). Şarkıları çalmak, kuyruğa eklemek, bir listeye eklemek, ZIP olarak indirmek ya da silmek için seç — örneğin bir mix’in geçen hafta getirdiklerini temizlemek için
- **Kitaplıkta aç** (listenin sayfası ya da sanatçı izlemesinde sanatçınınki), **Orijinali aç** ve **Şimdi kontrol et**

İzlemenin kimliği (`#12`) adının yanında görünür; böylece aynı bağlantının iki izlemesi — örneğin aynı listeyi takip eden iki hesap — ayırt edilebilir.

## Bir şarkının nereden geldiği

Kitaplığın herhangi bir yerinde bir şarkının menüsündeki **Nereden geldi**, onu ilk hangi izlemenin, ne zaman ve hangi sağlayıcıyla indirdiğini — ilk kontrolle geldiyse **İlk kontrol** — söyler ve şu anda onu tutan her izlemeyi kimliği, sahibi (yönetici için), şarkıyı ne zaman ve nasıl aldığıyla listeler: **İndirdi**, **Zaten kitaplıkta** ya da **Kayıttan önce**. Tek bir dosyadır: bir şarkıyı paylaşan izlemelerin hepsi aynı kopyayı gösterir.

Oradan **Etkinlik ve şarkılar** izlemenin sayfasını, **Kitaplıkta aç** da listesini açar. Bırakılmış ya da artık başka bir bağlantıyı izleyen bir izleme, indirdiği şarkıların kaynağı olarak gösterilmeye devam eder. Bu geçmiş yokken kaydedilmiş bir şarkı için onu ilk kaydeden izleme **Muhtemelen** işaretiyle gösterilir. Hiçbir izlemenin indirmediği bir şarkı (kendin indirdiğin) bunu söyler.

Bir kullanıcı kendi izlemelerini adlarıyla görür; başka bir hesabın izlemesinin indirdiği bir şarkı yalnızca bunu ve ne zaman olduğunu söyler.
