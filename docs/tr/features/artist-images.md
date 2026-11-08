---
icon: lucide/image
---

# Sanatçı fotoğrafı, afişi ve biyografisi

Downtify, Kitaplığınızdaki her sanatçı için oluşturulmuş bir baş harf ve hiç metin yerine gerçek bir profil fotoğrafı, bir afiş ve bir biyografi gösterebilir. Bu, yeni bir sanatçının sayfasını ilk kez açtığınızda ya da şarkılarından biri indirmeyi bitirdiğinde kendiliğinden dolar; sonrasında başka bir fotoğraf/afiş seçmek, yeniden almak veya kendi biyografinizi yazıp sosyal bağlantıları elle doldurmak size kalır.

Düzenleme, Kitaplıktaki her sanatçının sayfasında her zaman kullanılabilir; önce bir ayarı açmanız gerekmez.

::: info Ayarlar'daki "Sanatçı fotoğraflarını otomatik al" / "Sanatçı afişlerini otomatik al" hakkında
**Ayarlar → İndirmeler ve dosyalar → Sanatçı fotoğraflarını otomatik al / Sanatçı afişlerini otomatik al**, Downtify'ın bir sanatçının fotoğrafını/afişini kendiliğinden kaydedip kaydedemeyeceğini belirler — bu, bir sanatçının sayfasını ilk kez açtığınızda ve şarkılarından biri indirmeyi bitirdiğinde olur (bkz. [Yeni bir sanatçıyı ilk açtığınızda](#the-first-time-you-open-a-new-artist) ve [Bir indirme bittiğinde](#when-a-download-finishes)). Fotoğraflar varsayılan olarak açık, afişler kapalıdır. Düzenleme penceresini asla kısıtlamazlar: ayarları ne olursa olsun fotoğrafı veya afişi her zaman elle seçebilirsiniz.
:::

## Düzenleme penceresi

**Bir sanatçının afişi varsa, yuvarlak fotoğrafı sayfa başlığında gizlenir** — çoğunlukla afiş tek başına yeter, ikisini birden göstermek kalabalık duruyordu. Yine de fotoğraf kaybolmadı: düzenlemek için hâlâ orada, bir sekme ötede.

Kitaplıktaki bir sanatçı sayfasında (`/library/artist?name=…`), **Fotoğrafı düzenle** düğmesini görmek için yuvarlak fotoğrafın (gösteriliyorsa) üzerine, **Sanatçıyı düzenle** düğmesini görmek için afiş alanının üzerine gelin — ikisi de aynı pencereyi açar: üstte sanatçının mevcut fotoğrafı, altında dört sekmeli bir menü. Tıkladığınız düğmeye göre **Profil** veya **Afiş** ile açılır (fotoğraf her zaman tıklanabilir olmadığından varsayılan **Afiş**'tir).

- **Profil** / **Afiş** — ikisinde de bir görsel aynı şekilde seçilir:
  - **Adla ara** — YouTube Music ve Deezer'da eşleşen bir sanatçı fotoğrafı arar (yalnızca Deezer'ın genel yer tutucu görseline sahip Deezer sanatçıları dışarıda bırakılır). Başka bir adı aramak için başka bir şey yazın; ya da tek seferlik aday olarak kullanmak için doğrudan bir `http(s)://` görsel bağlantısı girin.
  - **Cihazdan yükle** — herhangi bir görsel dosyası.
  - **Fotoğrafı kaldır / Afişi kaldır** — yalnızca etkin sekmenin görseli kaydedildikten sonra gösterilir; onay ister, ardından yardımcı (sidecar) dosyayı siler.

  Her arama sonucu kartında nereden geldiğini gösteren bir rozet bulunur. Birini seçmek onu hemen indirip kaydeder. Görseli şu anda kayıtlı olan görsel olan kart, Profil ve Afiş sekmelerinde ayrı ayrı yeşil bir kenarlık ve onay işaretiyle belirtilir — böylece adaylardan hangisini kullandığınızı bir bakışta görürsünüz. Yüklediğiniz bir fotoğrafın ya da Downtify bunu hatırlamaya başlamadan önce kaydedilmiş bir fotoğrafın işaretlenecek bir kartı yoktur.
- **Biyografi** — şu anda kayıtlı biyografiyi (yoksa boş) gösteren, kendiniz yazıp düzenleyebileceğiniz düz bir metin kutusu. Kaydetmek mevcut metnin üzerine doğrudan yazar. Kutunun üstündeki ⚡ **Biyografiyi Streams'ten al** düğmesi, elle yazmak yerine kutuyu Apple Music/Deezer verileriyle doldurabilir — aşağıdaki [Biyografiyi otomatik alma](#fetching-a-bio-automatically) bölümüne bakın.
- **Sosyal medya** — Twitter/X, Instagram, Facebook, YouTube ve web sitesi bağlantıları, doğrudan düzenlenebilir. Kaydetmek, beş alanın hepsini formdakiyle değiştirir; boş bıraktığınız alan bile. Biyografi almak, sizin doldurduğunuz bir bağlantıya asla dokunmaz: Deezer'ın sosyal bağlantıları yalnızca henüz boş olan alanları doldurur (Deezer her ağı bilmez, bu yüzden gerisini elle tamamlayın, öyle kalır).

## Yeni bir sanatçıyı ilk açtığınızda

Kitaplıktaki bir sanatçının sayfasını açmak, profilini otomatik olarak oluşturur, ancak yalnızca onun için henüz hiçbir şey kaydedilmemişse — ilkinden sonraki her ziyaret hızlı bir no-op'tur, yani bu asla tekrarlanmaz ve çalıştıktan sonra hiçbir şeyi yavaşlatmaz.

- **Fotoğraf ve afiş** — Spotify'dan (aşağıdaki [Spotify](#spotify) bölümüne bakın); Spotify'da hiçbir şey yoksa YouTube Music'te tam ad eşleşmesine başvurulur. Yalnızca Ayarlar'da **Sanatçı fotoğraflarını otomatik al** ve/veya **Sanatçı afişlerini otomatik al**'ı açtıysanız (ikisi de varsayılan olarak kapalıdır ve her biri bağımsızdır); düzenleme penceresi her zaman ikisini de elle ayarlayabilir.
- **Biyografi, köken, kuruluş yılı, tür, grup işareti, afiş rengi, sosyal bağlantılar, benzer sanatçılar ve platform kimlikleri** — aşağıdaki [Biyografiyi otomatik alma](#fetching-a-bio-automatically) bölümünde anlatıldığı gibi Apple Music ve Deezer'dan alınır.

Bu çalışırken Apple Music veya Deezer **başarısız olursa** (erişilemiyor ya da istek sınırının üstünde), hiçbir şey kaydedilmez — ne biyografi ne fotoğraf — ve sayfa henüz bir profil göstermez, böylece sonraki ziyaret yeniden dener. Yalnızca sanatçıyı tanımadığını söyleyen bir servis yanıt sayılır: profil o zaman diğerinin sahip olduğuyla oluşturulur. Spotify kısmı (benzer sanatçılar) bir profilin oluşmasını asla engellemez.

## Bir indirme bittiğinde

Bir sanatçının şarkılarından biri indirmeyi bitirdiğinde — uygulamada siz başlatmış olun ya da bir [Çalma listesi izleyici](playlist-monitor.md) taraması — o sanatçının henüz profili yoksa aynı oluşturma arka planda çalışır; böylece indirdiğiniz sanatçılar sayfalarını açmadan önce hazır olur. İndirmeyi asla yavaşlatmaz: sanatçı kuyruğa alınır ve birkaç saniye sonra, aynı anda iki sanatçı olacak şekilde doldurulur; kuyrukta olan bir sanatçı, kaç şarkısı gelirse gelsin yeniden kuyruğa alınmaz (bir sanatçının elli şarkılık çalma listesi onu bir kez oluşturur). Kitaplığınızda zaten olan şarkılar yeniden indirilmez ve hiçbir şeyi tetiklemez.

- **Hangi sanatçı** — dosyanın altına arşivlendiği sanatçı: albüm sanatçısı, yoksa ilk anılan sanatçı. `Various Artists` atlanır.
- **Dil** — biyografi ve tür, sayfanın sunucuda tuttuğu web arayüzü dilinde gelir (bkz. [Uluslararasılaştırma](internationalization.md)); bir sayfa bunu bildirene kadar İngilizce.
- **Fotoğraf ve afiş** — yalnızca **Sanatçı fotoğraflarını otomatik al** / **Sanatçı afişlerini otomatik al**'ın izin verdiği kadar, o anda okunarak; bu yüzden bir ayarı değiştirmek hemen sonraki şarkıya uygulanır.
- **Top songs** — bu şekilde oluşturulmaz; sanatçı sayfasını bekler (bkz. [Top songs](top-songs.md)).

Bir sanatçı için hiçbir yerde hiçbir şey bulunamazsa, bu yine de yalnızca bir kez çalışır — sonraki her ziyarette yeniden denemez. Daha sonra istediğiniz an fotoğrafı/afişi elle seçmek ya da alma düğmesini yeniden denemek için düzenleme penceresini kullanın.

## Bağlantılar sekmesi

En az bir kayıtlı bağlantısı olan sanatçı, **Biyografi**'den hemen önce (son sekme olarak kalır) bir **Bağlantılar** sekmesi alır; üzerinde kaç tane olduğunu gösteren bir sayaç bulunur. Bağlantıları kartlar olarak listeler; her ekranda ve sanatçının afişi olsun olmasın: önce **Yayın platformları**, sonra **Sosyal medya**. Her kart sitenin adını ve adresini gösterir ve onu yeni bir sekmede açar. Yalnızca gerçekten kayıtlı olanlar listelenir ve bağlantısı olmayan sanatçının Bağlantılar sekmesi yoktur (onun için `?tab=links` ilk sekmeyi açar).

- **Yayın platformları** — Spotify, YouTube Music, Deezer ve Apple Music, profilin `platforms_id` alanından oluşturulur: kayıtlı her kimlik bir bağlantıya dönüşür (örn. kayıtlı bir Deezer kimliği, o sanatçının Deezer sayfasına bir bağlantı olur). Kimliklerin hepsi, bir biyografi ilk kez alındığında her platformda tam ad eşleşmesiyle otomatik çözülür (Spotify'ınki, varsa sanatçının kendi Spotify şarkılarından birinden gelir; bu da aynı adlı birini seçemez). Sanatçı profilinin JSON'unda (aşağıya bakın) elle bir tane ekleyebilir veya düzeltebilirsiniz.
- **Sosyal medya** — Twitter/X, Instagram, Facebook, YouTube ve web sitesi: yukarıdaki Sosyal medya sekmesinin boş olmayan her alanı için bir kart. Yalnızca web adresleri açılır: `https://` olmadan girilmiş bir bağlantıya bu eklenir, başka türden bir adrese sahip her şey (örneğin bir `javascript:`) yok sayılır.

## Spotify

Spotify hiçbir zaman serbest metinli bir arama kaynağı olarak görünmez, ancak hem seçici hem de ilk ziyaretteki otomatik oluşturma (yukarıya bakın) sanatçıyı yine de orada bulur. Önce sanatçının kendi indirilmiş şarkılarından birkaçına bakarlar: biri Spotify'dan indirildiyse Downtify o şarkının Spotify kimliğini zaten bilir ve görseli doğrudan çözer — aynı adlı başka bir sanatçıya düşemeyeceği için en güvenilir yol. Hiçbir şarkı Spotify'dan gelmediğinde (diyelim YouTube'dan indirildi), sanatçı tam adla aranır (büyük/küçük harfe bakılmaz — bulanık eşleşme asla kullanılmaz). Seçicide bu aday ilk sırada, **Spotify** etiketiyle görünür.

Ad araması Spotify'ın kendi web oynatıcısının arama kutusunu kullanır, bu yüzden Spotify'ın değiştirebileceği dahili bir tanımlayıcıya bağlıdır; bu olursa Downtify başarısız olmak yerine fotoğraf/afiş için YouTube Music'e başvurur ve Spotify kimliğini boş bırakır.

Fotoğraf ve afiş, Spotify'da gerçekten farklı görsellerdir ve farklı şekilde çözülür: kare fotoğraf sanatçının herkese açık gömme sayfasından, geniş afiş ise Spotify'ın kendi sanatçı sayfası verilerinden gelir (gömme bunu hiç sunmaz). Her sanatçının afişi yoktur — yoksa kare fotoğrafa başvurmak yerine afiş seçicisine hiçbir Spotify adayı sunulmaz.

Spotify kaynaklı şarkısı olmayan bir sanatçı yine de basitçe Spotify adayı almaz — YouTube Music/Deezer'da arayın, bir bağlantı yapıştırın veya bir görsel yükleyin.

## Biyografiyi otomatik alma

Sanatçı sayfası, başlığın altında kısa, salt okunur bir biyografi gösterir — bir tane kaydedilene kadar boştur. Doldurmak için düzenleme penceresinin **Biyografi** sekmesini açın ve metin kutusunun üstündeki **Apple Music'ten getir** veya **Deezer'dan getir**'e tıklayın (bkz. [Kaynağı seçme](#choosing-the-source)); bu, o servisin biyografisini incelemeniz ve kaydetmeniz için kutuya yükler. Kendiliğinden kaydeden ilk ziyaretteki otomatik oluşturma, sanatçıyı Apple Music'te tam ad eşleşmesiyle arar (Apple'ın kendi Müzik uygulamasının kullandığı ad aramasıyla) ve biyografisini, kökenini, kuruluş yılını, türünü, grup işaretini ve afişin vurgu rengini alır — metni (biyografi ve tür) arayüzünüzün mevcut dilinde — ve sonucu kaydeder. Tür (Apple Music sanatçı başına bir tane verir, örn. "Hard rock"), sanatçı sayfasının Biyografi sekmesinin üstünde, köken ve kuruluş yılının yanında küçük bir hap olarak görünür. Apple Music sanatçının grup olup olmadığını söyler: bir grup için bu tarih "1995 yılında kuruldu", tarihi genelde doğum tarihi olan solo sanatçı için "27 Eylül 1984 doğumlu" olarak okunur (tüm arayüz dillerine çevrilmiştir; grup işareti bilinmeyen bir sanatçı "kuruldu" olarak kalır). Tarihin kendisi Apple Music'in verdiği gibi gösterilir, dolayısıyla almanın dilini korur. Apple Music'te tam eşleşme yoksa ya da var ama dilinizde biyografi metni yoksa, sıradaki ikincil biyografi kaynağı olarak Deezer denenir — ayrıca sosyal bağlantılar ve "hayranlar bunları da sever" benzer sanatçı adları getirir (benzer sanatçılar sanatçının profil dosyasına kaydedilir ama henüz hiçbir yerde gösterilmez, gelecekteki bir ekleme için saklanır) ve Sosyal medya sekmesini de doldurur. Yalnızca iki kaynakta da hiçbir şey yoksa tahmin edilmiş/yanlış bir biyografi yerine bir hata görürsünüz.

Apple Music'in editoryal biyografileri her sanatçı için her dilde yazılmaz — belirli bir sanatçı için bir dil eksikse, bunun yerine Deezer'ın biyografisi (varsa) kullanılır; köken/kuruluş yılı/grup işareti ise çevrilmiş metin olmadığından yine Apple Music'ten gelir (tür her zaman yalnızca Apple Music'ten gelir, dolayısıyla Apple'ın eşleşmesi yoksa boş kalır). Birkaç dil (yazım sırasında Bulgarca) Apple Music tarafından hiç sunulmaz ve her zaman onun varsayılan dildeki biyografisine düşer.

Biyografi, sanatçının JSON'unda düz metin olarak saklanır — HTML etiketi ve madde işareti karakteri olmadan: boş bir satır paragrafları ayırır ve bir Apple Music biyografisindeki her `•` madde işareti (Apple bunları tek bir satır sonuyla ayırır) kendi paragrafı olur. Deezer'ın HTML biyografileri de aynı şekilde düzleştirilir (her paragraf boş satırla ayrılmış bir paragraf olur, diğer her etiket atılır). Sanatçı sayfası her paragrafı ayrı gösterir ve içindeki tek satır sonlarını korur; Biyografi sekmesindeki metin kutusu tam olarak bu metni düzenler.

Bu şekilde yeniden almak yalnızca düğmeye tıkladığınızda çalışır — yukarıda anlatılan ilk ziyaretteki otomatik oluşturmadan sonra kendiliğinden hiçbir şeyin üzerine yazmaz. Yalnızca ilk seferde (otomatik oluşturma ya da elle tıklama) ada göre aramak gerekir: çözülen Apple Music ve Deezer sanatçı kimlikleri sonrasında sanatçının profil dosyasında önbelleğe alınır, böylece yeniden almak aynı sanatçıları doğrudan yeniden okur.

Kayıtlı bir biyografiyi temizlemek için Biyografi sekmesini açın, metin kutusunu boşaltın ve Kaydedin — köken, kuruluş yılı, tür, grup işareti, sosyal bağlantılar, benzer sanatçılar ve önbellekteki platform kimlikleri olduğu gibi kalır.

## Kaynağı seçme

Biyografi sekmesinde metin kutusunun üstünde iki bağlantı vardır; hangi biyografinin daha iyi okunduğunu seçebilmeniz için:

- **Apple Music'ten getir** — Apple Music'in editoryal biyografisini metin kutusuna yükler. Apple Music'te bu sanatçı için dilinizde hiçbiri yoksa, bir yedek yerine hata alırsınız.
- **Deezer'dan getir** — Apple Music'te bir tane olsa bile Deezer'ın biyografisini yükler. Deezer'da hiçbiri yoksa hata alırsınız.

Bir bağlantıya tıklamak **yalnızca metin kutusunu doldurur** — **Kaydet**'e basana kadar hiçbir şey kaydedilmez; böylece okuyabilir, düzenleyebilir veya önce diğer servisi deneyebilirsiniz ve pencereyi kaydetmeden kapatmak mevcut biyografiyi olduğu gibi bırakır. Yalnızca biyografi metni yüklenir: köken, kuruluş yılı, tür, sosyal bağlantılar, benzer sanatçılar ve platform kimliklerine bu bağlantılar dokunmaz (onları ilk ziyaretteki otomatik oluşturma doldurur). Otomatik oluşturma hangi servis olduğunu sormaz: Apple Music'in biyografisini kullanır ve yalnızca Apple Music'te hiçbiri yoksa Deezer'ınkine başvurur.

## Dosyalar nereye gider

```
<downloads>/.metadata/ArtistImage/<Artist>.jpg
<downloads>/.metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/.metadata/ArtistData/<Artist>.json
<downloads>/.metadata/ArtistTopSongs/<Artist>.topsongs.json
```

Sanatçı başına bir dosya, onun adıyla (şarkı dosya adlarıyla aynı şekilde temizlenmiş) — veritabanı kaydı yoktur, bu yüzden dosyanın diskte bulunması sanatçı sayfasının kontrol ettiği şeydir. Yeni bir fotoğraf/afiş kaydetmek öncekinin üzerine yazar (web arayüzü eskisinin kopyasını göstermeyi sürdürmesini önler: kayıtlı her görselin URL'si dosyanın değiştirilme zamanını taşır, böylece değiştirilen fotoğraf yeniden alınırken dokunulmamış olan önbellekte kalır) ve `ArtistData/<Artist>.json`, yukarıda anlatılan biyografi/sosyal medya/benzer sanatçılar/platform kimliği verilerini tutar; ayrıca `current_cover` ve `current_cover_banner` içinde hangi görselin mevcut fotoğraf/afiş olduğunu: indirildiği URL'nin yolunu (host ve query atılır, böylece başka bir CDN adresindeki aynı görsel yine eşleşir) ya da yüklediğiniz için `upload` değerini tutar. Düzenleme penceresi, kullanımda olanı işaretlemek için her adayı bununla karşılaştırır. Bunlar indirme klasörünüzdeki sıradan dosyalardır, dolayısıyla Navidrome gibi servisler aynı konuma yönlendirirseniz onları doğrudan okuyabilir.

Sanatçı adları diskin tuttuğu şekilde eşleştirilir: Downtify `AC/DC`'yi `ACDC` olarak arşivler, çünkü bir dosya adı `/` içeremez ve sanatçı etiketi olmayan bir şarkı sanatçısını o dosya adından alır — dolayısıyla aynı sanatçı `AC/DC` veya `ACDC` olarak görünebilir. Her ad araması (Spotify, Deezer, YouTube Music ve Apple Music) büyük/küçük harfi ve dosya adının taşıyamadığı karakterleri yok sayar, böylece iki yazım da aynı sanatçıyı bulur ve yukarıdaki aynı dosyaları paylaşır. Başka bir şeyde farklılaşan bir ad — örneğin `AC/DC Tribute` — hâlâ başka bir sanatçıdır ve asla eşleşmez.

`platforms_id`, `spotify`, `youtubemusic`, `deezer` ve `applemusic` anahtarlarını tanır; hepsi otomatik çözülür — Spotify, sanatçının kendi Spotify şarkılarından birinden ya da o yoksa tam adla; diğerleri tam adla. Biyografi almak, eksik bir Spotify kimliğini de doldurur; böylece bu özellik var olmadan önce açılmış bir sanatçı, bir almadan sonra Spotify simgesini alır. Zaten kayıtlı bir kimliğin yerine asla başkası yazılmaz ve elle bir tane ayarlamak için JSON dosyasını yine doğrudan düzenleyebilirsiniz.

## Kapsam dışı

Burada bir fotoğraf/afiş seçmek indirme hattına asla dokunmaz — kendi ses dosyalarınızın etiketlerine gömülenler üzerinde hiçbir etkisi yoktur ve bir şarkı indirmek sanatçı görselini asla otomatik almaz.

*Benzer* sekmesi, sahip olmadığınız sanatçılar için de bir fotoğraf gösterir; Kitaplığın *Sanatçılar* ızgarası, sanatçının kendi sayfası, İzleyicinin *Sanatçılar* sekmesi (izlediğiniz sanatçı, listede ve düzenleme penceresinde) ile [Keşfet](discover.md) ve [Finder](finder.md)'daki sanatçılar da öyle — sayfanın sanatçının Deezer görselini zaten taşıdığı yerlerde ad araması gerekmez ve sanatçı için kaydettiğiniz fotoğraf varsa onun yerine o görünür — fotoğrafını seçmediğiniz her sanatçı için (Deezer'da hiçbiri yoksa Kitaplık ve sanatçının kendi sayfası sanatçının şarkı kapaklarından birini kullanır; İzleyicide şarkı yoktur, bu yüzden baş harfleri gösterir) - yalnızca gerçek bir fotoğraf: Deezer'ın fotoğrafı olmayan bir sanatçı (genel bir yer tutucu görsel sunar) her zamanki baş harfini alır - ancak bu yalnızca görüntüleme içindir: sunucu Deezer görselini kaydetmeden tarayıcınıza iletir (tarayıcı bunu üç saat önbelleğe alır) ve görsel asla bir sanatçının fotoğrafı veya afişi olmaz. Yalnızca gerçek yanıtlar tutulur: Deezer'a o anda ulaşılamıyorsa ya da istek sınırının üstündeyseniz kutucuk şimdilik baş harfi (veya şarkı kapağını) gösterir ve hiçbir şey hatırlanmaz, böylece fotoğraf sayfayı bir sonraki açışınızda görünür. Fotoğraflar diske yalnızca kendiniz birini ayarladığınız ya da fotoğrafı/afişi yukarıda anlatıldığı gibi ilk ziyarette kaydedilen sanatçılar için yazılır (Ayarlar izin verdiğinde). Bkz. [`GET /api/artists/photo-proxy`](../api-reference.md#get-apiartistsphoto-proxy).
