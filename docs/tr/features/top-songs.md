---
icon: lucide/star
---

# Top Songs

Bazı sanatçıların yalnızca bir avuç parçanın önem taşıdığı devasa katalogları vardır. Bağlantıları parça parça almak ya da gerçekten istediğiniz birkaç şarkı için 50’den fazla parçalık bir “This is…” çalma listesi indirmek yerine, sanatçının kendi bağlantısını yapıştırın ve en popüler şarkıları arasından seçin.

## Nasıl kullanılır

1. Bir sanatçı bağlantısını arama kutusuna veya Ana sayfa ekranına yapıştırın:
   - **Spotify**: `https://open.spotify.com/artist/…`
   - **YouTube Music**: `https://music.youtube.com/channel/UC…` veya `https://music.youtube.com/@handle`
   - **Deezer**: `https://www.deezer.com/artist/…`
2. **Sanatçı sayfası** fotoğrafı ve adıyla açılır ve yayınlarını (hizmetin sahip olduğu albümler, single’lar, EP’ler ve derlemeler) Spotify ve Deezer’da en yeniden eskiye listeler; parçalarını görmek veya indirmek için birine tıklayın. **Top Songs** düğmesinin yanında, Spotify ve YouTube Music sanatçılarında ayrıca **Yeni yayınları izle** de vardır — Deezer sanatçılarında yoktur, çünkü [Çalma Listesi İzleyici](playlist-monitor.md) Deezer’ı desteklemez.
3. **Top Songs**, en popüler şarkılarının listesini hizmetin sıraladığı düzende açar. Spotify ve YouTube Music’te göz simgeli bir rozet, her şarkının kaç kez çalındığını diliniz neyse o şekilde kısaltarak gösterir (Portekizce’de `1,5 bi`, İngilizce’de `1.5B`) — Spotify’ınki yeşil, YouTube Music’inki kırmızıdır. YouTube Music yalnızca yuvarlanmış bir sayı bildirir (`1.2B plays`), dolayısıyla onun sayısı bir yaklaşıklıktır; Downtify bunu şarkıları listeleyen aynı YouTube Music isteğinden okur, bir de çalma sayıları için ek bir istek yapar. Deezer’ın kendi “top” sıralamasında gösterilecek herkese açık bir çalma sayısı yoktur; bu yüzden şarkıları rozetsiz listelenir. İlk beşi zaten işaretlidir; daha fazlasını işaretleyin veya herhangi birinin işaretini kaldırın, sonra **Seçilenleri indir**’e basın.

### İndirmeden önce şarkı çalma

Top Songs sayfasında ve yapıştırılmış bir **albüm** ya da **çalma listesi** bağlantısının açtığı sayfada her şarkı tam olarak çalar: satırının üzerine gelin, numara bir oynat düğmesine dönüşür (telefonda oynat düğmesi her zaman oradadır); basın, şarkı YouTube’dan doğrudan yerleşik oynatıcıya akıtılır. Duraklatmak için yeniden basın ya da geçiş için başka bir satırın düğmesine basın. Kitaplığınızda zaten olan bir şarkı bunun yerine kitaplıktan çalar; listedeki diğer indirilmiş şarkılar ondan sonra sıraya alınır.

Akış bu sunucudan sunulur, asla tarayıcıdan doğrudan YouTube’a gitmez: satır kendi YouTube videosuna çözümlenir (bir YouTube Music şarkısı için kendi videosu, aksi halde en yakın arama eşleşmesi) ve sunucu sesi bir kez akış önbelleğine indirir, sonra önbellekteki dosyayı çalar (bkz. [`GET /api/stream/file`](../api-reference.md#get-apistreamfile)). Yalnızca sunucunun YouTube’a erişebilmesi gerekir ve yaş sınırlı bir parça, bir indirme gibi YouTube çerezleri ister (bkz. [YouTube çerezleri](youtube-cookies.md)).

## Kaynaklar

| Kaynak | “Top songs”un anlamı | Listelenen şarkılar |
|--------|------------------------|--------------|
| Spotify | Sanatçının kendi **Popüler** rafı; Spotify sayfasının en üstünde gösterilen aynı parçalar | En fazla 10 |
| YouTube Music | Sanatçının **Top songs** çalma listesi, popülerliğe göre sıralı | İlk 50 |
| Deezer | Sanatçının kendi **top** sıralaması (`deezer.com`’un sayfasında gösterdiği aynı raf) | İlk 50 |

Spotify’ın herkese açık embed’inde diskografi yoktur; bu yüzden Downtify yayınları Spotify web oynatıcısının kendi diskografi sorgusundan okur; albüm adları için kullandığı aynı herkese açık olmayan API’dir. Spotify bunu değiştirirse Downtify daha kısa bir listeye döner (tüm albümler ama yalnızca en yeni on single) ve o da olmazsa hiç yayın göstermez. Spotify şarkıları, albüm adı baştan eklenmiş olarak olağan üst veri-sonra-ses eşleştirme işlem hattından geçer; indirme geri kalanı (parça numarası, yıl) her Spotify şarkısında olduğu gibi doldurur. YouTube Music şarkıları, diğer her YouTube Music bağlantısı gibi kendi videosuna sabitlenir. Deezer’ın gerçek, herkese açık bir diskografi uç noktası vardır; bu yüzden yayın listesi bir yedeğe ihtiyaç duymaz; şarkıları Spotify’ınkilerle aynı üst veri-sonra-ses eşleştirme işlem hattından geçer ve Deezer sunuyorsa 30 saniyelik bir önizleme klibi eklenir.

## Kitaplıktaki bir sanatçının sayfasında

Downtify’ın Spotify’da tanıdığı bir sanatçı ([Sanatçı fotoğrafı, afişi ve biyografisi](artist-images.md) bölümüne bakın), Kitaplığınızdaki sayfasında Parçalar ve Hayranlar bunları da seviyor sekmelerinin yanında bir **Top songs** sekmesi de alır. Spotify top şarkılarının ilk **5**’ini, arama sonuçları gibi sade bir liste olarak sütun başlıkları altında (#, Başlık, Albüm, süre) listeler: numara, kapak, başlık, sanatçı, albüm ve süre. Kitaplığınızda olmayan bir şarkının sağında bir **indirme** düğmesi vardır (indirilirken ilerlemesiyle); indirildikten sonra **Kitaplıkta** etiketine dönüşür ve şarkı bir albüm sayfasındaki gibi çalınabilir: numara üzerine gelince oynat düğmesine dönüşür, kapak çalar, çift tıklama veya dokunma da çalar. Birini çalmak, listedeki diğer indirilmiş şarkıları sıralama düzeninde ondan sonra sıraya alır ve çalan şarkı vurgulanır. Henüz indirilmemiş bir şarkı bunun yerine **tam olarak akıtılır**: satırının üzerine gelin, numaranın olduğu yerde bir oynat düğmesi belirir; ona (veya kapağa) basın, indirilmiş bir şarkı gibi yerleşik oynatıcıda çalar (bkz. [İndirmeden önce şarkı çalma](#playing-songs-before-downloading)). Listenin altında **Daha fazla popüler şarkı**, bu sanatçıyı yukarıda anlatılan Top Songs sayfasında açar; seçim, **Çalma listesi oluştur** anahtarı ve birkaçını birden indirme oradadır. Sekme yalnızca sanatçının Spotify kimliği bilindiğinde görünür; bu da sayfası ilk açıldığında olur; şarkılar tam o sırada istenir, dolayısıyla sekmenin sayısı sayfanın neresinde olursanız olun birkaç saniye sonra kendiliğinden dolar.

Bir şarkının kapağını, albümünü ve çalma sayısını okumak birkaç saniye sürer; bu yüzden Downtify beş şarkıyı sanatçı başına bir dosyada tutar: `<downloads>/.metadata/ArtistTopSongs/<Sanatçı>.topsongs.json`; sanatçının sayfası ilk açıldığında arka planda yapılır. **7 gün** boyunca güvenilir sayılır: sekmeyi açmak dosyayı hemen okur ve bundan eskiyse eski liste hemen gösterilirken arkada yenisi getirilir — sayfa onu birkaç saniye içinde kendiliğinden değiştirir, indirilen ya da çalan bir şarkıyı rahatsız etmeden. Dosya yalnızca şarkıları, kapak görsellerini, klip bağlantılarını ve çalma sayılarını tutar — asla sesi veya görüntüleri, ve asla bir şarkının kitaplığınızda olup olmadığını, çünkü bu anlık hesaplanır. Bir önbellektir: dilediğinizde silin, yeniden yapılır.

## Çalma listesi oluşturma

Top Songs sayfasındaki **Çalma listesi oluştur** anahtarı bir sanatçıyı ilk açışınızda **kapalı** başlar; kitaplığınızda **Top Songs of {artist}** adlı bir çalma listesi zaten varsa **açık** başlar, böylece sonraki indirmeler ona eklenmeye devam eder. Anahtarı çevirin; seçiminiz o sayfada olduğunuz sürece kalır. Kapalıyken şarkılar diğer tek tek şarkılar gibi indirilir: doğrudan indirme klasörünüze ya da [Dosya düzeni](file-organization.md) açıksa sanatçı/albüm klasörlerinize, kendi klasörü, M3U’su ve sanatçı fotoğrafı olmadan.

Açın; Downtify onları **Top Songs of {artist}** adlı bir çalma listesi olarak ele alır. Nereye gittiği Dosya düzenine bağlıdır:

| Sanatçıya / albüme göre düzenle | Şarkılar | M3U ve kapak |
|---|---|---|
| İkisi de kapalı | `Top Songs of {artist}` adlı bir klasörde | Aynı klasörde |
| Biri veya ikisi açık | Bu ayarlara göre dosyalanır: `<Sanatçı>/`, `<Albüm>/` veya `<Sanatçı>/<Albüm>/`. `Top Songs of {artist}` klasörü yoktur. | `Playlists/` içinde, `Top Songs of {artist}.m3u` ve `.jpg` olarak |

Her iki durumda:

- [M3U çalma listesi](m3u-export.md) şarkıları yalnızca bazılarını işaretlemiş olsanız bile **sanatçının sıralama düzeninde** listeler;
- **Çalma listesi kapağını kaydet** etkinse sanatçının fotoğrafı, M3U’nun yanına kapağı olarak kaydedilir (bkz. [Çalma listesi kapağı](playlist-cover-art.md)). Bunun için ayrı bir ayar yoktur.

## Bilinen sınırlamalar

::: warning Aynı sanatçı için Spotify ve YouTube Music’i karıştırma
**Top Songs of {artist}** M3U’su, Spotify parça kimlikleriyle anahtarlanan [çalma listesi kataloğundan](library-catalog.md) eşzamanlı tutulur. Bir sanatçının top şarkılarını **Spotify**’dan, sonra **YouTube Music**’ten (veya tersi) indirirseniz, ikinci grubun dosyaları doğru iner ama sonraki M3U yenilemesi onları çalma listesi dosyasından düşürür; çünkü YouTube Music kimlikleri o biçime uymaz. **Aynı** kaynaktan daha fazla şarkı eklemek etkilenmez.
:::

::: info Spotify şarkıları için albüm adları
Spotify’ın sanatçı sayfası bir şarkının hangi albümden olduğunu söylemez. Downtify albüm adlarını ve çalma sayılarını, tam çalma listelerini okumak için kullandığı aynı Spotify oynatıcı API’sinden alır: sanatçı başına bir ek istek, artı o isteğin listelemediği her albüm için bir tane. Bu API herkese açık değildir; Spotify onu değiştirirse Spotify şarkılarında **Albüm** sütunu boş gelir ve çalma sayısı rozeti kaybolur; şarkılar yine de iner, ama Downtify o zaman albümü YouTube Music eşleşmesinden kurtarmak zorunda kalır; bu çoğu zaman başarısız olur, dosyayı albüm etiketsiz bırakır ve [Albüme göre düzenle](file-organization.md) açıksa `unknown` albüm klasörüne koyar. YouTube Music top şarkıları albümlerini zaten taşır. Çalma sayıları, iki kaynaktan birinde gelmeyi bırakırsa rozet sadece görünmez.
:::

## API

API Başvurusu’nda [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl) bölümüne bakın.
