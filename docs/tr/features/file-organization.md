---
icon: lucide/file-headphone
---

# Dosya düzeni

Yeni bir sunucu dosyaları sanatçı ve albüme göre düzenler (`Sanatçı/Albüm/…`): **Sanatçıya göre düzenle** ve **Albüme göre düzenle** varsayılan olarak açıktır. Aşağıdaki düz yapıyı elde etmek için ikisini de kapatın. Bu varsayılandan önce kurulmuş sunucular önceki seçimlerini korur.

## Düz yapı (ikisi de kapalı)

Tekil parçalar ve YouTube aramaları doğrudan indirme klasörünün köküne gider. Çalma listesi ve albüm parçaları, çalma listesi veya albüm başına bir alt klasöre gider:

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← tekil parça
```

## Sanatçıya göre düzenle

**Ayarlar → İndirmeler ve dosyalar → Sanatçıya göre düzenle** açıkken (varsayılan) çalma listesi ve albüm indirmeleri dahil her parça, albüm sanatçısının adını taşıyan bir alt klasörde toplanır (bkz. [Birden çok sanatçı ve derlemeler](#several-artists-and-compilations)):

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

Bu yapı, `Sanatçı/Şarkı.ext` klasör düzeni bekleyen medya sunucuları (Jellyfin, Navidrome, Plex) ve kitaplık yöneticileriyle (Beets) uyumludur.

## Birden çok sanatçı ve derlemeler

Bir şarkıda çoğu zaman birden çok sanatçı yer alır. Downtify hepsini dosyanın **Sanatçı** etiketinde tutar ve ayrıca her birini ayrı ayrı bir **ARTISTS** etiketine yazar (MP3'te `TXXX:ARTISTS`); böylece bir oynatıcı `Earth, Wind & Fire` gibi bir adı virgülünden bölmek zorunda kalmaz. Klasör ise tek bir sanatçıya aittir: **albüm sanatçısına**, bir derlemede de parçanın ilk sanatçısına.

- Albüm sanatçısı, kaynağın (Spotify, YouTube Music veya Deezer) **albüm** için belirttiği sanatçıdır; albümün her parçasında aynıdır ve **Albüm sanatçısı** etiketine yazılır. Kaynak belirtmiyorsa parçanın ilk sanatçısıdır.
- Bir ikili ya da grup tek bir sanatçıdır. YouTube Music bazı grupları üyeleriyle, her girişte bir kişi olarak gösterir (`Henrique & Juliano`, albümde ve her parçada `Henrique` ve `Juliano` olarak gelir — bazen ters sırada, `Jorge & Mateus` için `Mateus` ve `Jorge`). Gösterilen her ad bir YouTube Music kanalına bağlanır; bir üyenin bağlantısı, yanındaki adlardan oluşan grubun tamamının adını taşıyan bir kanala gidiyorsa Downtify bu adları yeniden grubun adında birleştirir: klasör ile **Albüm sanatçısı**, **Sanatçı** ve **ARTISTS** etiketlerinin hepsi `Henrique & Juliano` olur. Gerçek bir iş birliği (her sanatçı kendi kanalında) tüm sanatçıları korur. YouTube Music hiçbir üyeyi grubun kanalına bağlamıyorsa adlar ayrı kalır; yine de Kitaplık, her zaman yalnızca başka birinin yanında geçen bir ada sayfa açmaz (bkz. [Kitaplık kataloğu](library-catalog.md#library-page)).
- Bir konuk sanatçı bunu asla değiştirmez. Michael Jackson'ın *Thriller* albümündeki konuklu *The Girl Is Mine*, `Michael Jackson/Thriller/` içinde kalır; *Lady Marmalade* single'ı (Christina Aguilera, Lil' Kim, Mýa, P!nk) ise `Christina Aguilera/` klasörüne gider.
- Yalnızca kaynağın kendisinin **Various Artists** olarak belirttiği bir albüm (bir film müziği, bir "Now That's What I Call…") derlemedir — siz [kendiniz işaretlemedikçe](#marking-an-album-as-various-artists). Tek bir YouTube Music şarkısı asla derleme değildir: YouTube Music aynı sesi birden çok yayında tutar ve bunlardan herhangi birini, çoğu zaman bir derlemeyi, albümü olarak gösterebilir; bu yüzden yalnızca tam bir YouTube Music albümü indirmesi sayılır. Parçaları albüm sanatçısı olarak "Various Artists" ve derleme işaretini alır (MP3'te `TCMP`, FLAC/Ogg/Opus'ta `COMPILATION`, M4A'da `cpil`). Bu, albümleri klasöre göre değil bu etiketlere göre gruplayan Navidrome ve diğer medya sunucularında albümü bütün tutar. Diskte ise **Sanatçıya göre düzenle** asla bir `Various Artists` klasörü oluşturmaz: her parça kendi ilk sanatçısının klasörüne gider.
- Downtify'ın eski sürümleri birden çok sanatçılı her şarkıyı, derleme işareti olmadan **Various Artists** olarak etiketlerdi. Kitaplık böyle bir şarkıyı eskisi gibi ilk sanatçısının albümünde göstermeye devam eder; **Çeşitli Sanatçılar olarak işaretle** albümü gerçek bir derleme yapar.

```
downloads/
├── Christina Aguilera/
│   ├── Lady Marmalade/
│   │   └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
│   └── Moulin Rouge/                  ← film müziğinden (bir derleme)
│       └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
└── David Bowie/
    └── Moulin Rouge/                  ← aynı film müziği
        └── David Bowie - Nature Boy.mp3
```

Single'daki ve *Moulin Rouge* film müziğindeki *Lady Marmalade* iki ayrı yayındır, her biri kendi albümüyle düzenlenir. Film müziğinin parçaları sanatçılarının klasörlerine dağılır ama tek bir "Various Artists" derlemesi olarak etiketlenir; bu yüzden Kitaplık ve medya sunucuları *Moulin Rouge*'u yine tek bir albüm olarak gösterir.

### Bir albümü Çeşitli Sanatçılar olarak işaretleme

Bir kaynak, birkaç sanatçıya eşit ölçüde ait bir yayını tek bir sanatçıya bağlayabilir — Deezer *Lady Marmalade* single'ını yalnızca Christina Aguilera altında listeler. Bir yönetici bunu Kitaplık'taki albüm sayfasından, **Kuyruğa ekle**'nin yanındaki **Çeşitli Sanatçılar olarak işaretle** düğmesiyle düzeltebilir.

- Albümün her parçası albüm sanatçısı olarak "Various Artists" ve derleme işaretini alır. Dosyalarda başka hiçbir şey değişmez ve dosyalar yerinde kalır (bir derlemenin parçaları zaten ilk sanatçılarının klasöründedir). Her dosya bir çalışma kopyası üzerinden yeniden yazılır, değişiklik tarihini korur ve yeniden yazma başarısız olursa dokunulmadan kalır.
- Kitaplık'ta albüm artık **Albümler** altında **Various Artists** ile listelenir (her parça kendi sanatçısının sayfasında kalır) ve albüm sayfası onu oraya kadar izler.
- Downtify albümü hatırlar: ondan daha sonra indirilen bir parça da aynı şekilde etiketlenir.
- Bir derlemede aynı düğme **Çeşitli Sanatçılar işaretini kaldır** olur: işareti geri alır ve albümün önceki albüm sanatçısını geri koyar. Kaynağının derleme yaptığı bir albümde de çalışır; o zaman albüm sanatçısı, parçalarının çoğunun ilk sıraya koyduğu sanatçı olur ve o albümün sonraki indirmeleri yeniden işaretlenmez.

Düğmeyi yalnızca yöneticiler görür. Medya sunucuları değişikliği bir sonraki kitaplık taramasında alır.

## M3U ve sanatçı klasörleri

*Sanatçıya göre düzenle* açıkken M3U üretimi de açıkken bir Spotify çalma listesi indirirseniz M3U, çalma listesi alt klasörünün içine değil `<downloads>/Playlists/<çalma-listesi-adı>.m3u` yoluna konur. Bunun nedeni, parçaların artık birden çok sanatçı klasörüne dağılmış olmasıdır. M3U içindeki göreli yollar, kitaplığı nereye bağlarsanız bağlayın doğru çözülmeye devam eder.

## Ayarı değiştirme

Ayar, tüm **yeni** indirmeler için hemen etkili olur. Diskte zaten bulunan dosyalar taşınmaz.

## Bir parçayı silmek boş klasörleri temizler

Kitaplık sayfasından bir parçayı silmek, boşaldığı anda onun çalma listesi, sanatçı veya albüm klasörünü de kaldırır — ve artık boş kalan üst klasörlerden de yukarı doğru devam eder (örneğin son albümü gittikten sonra sanatçı klasörü), hiçbir zaman kaldırılmayan indirme dizininin kendisinde durur. İçinde başka bir şey bulunan klasöre — başka bir parça, bir `.m3u`, hâlâ kullanılan bir `cover.jpg` — dokunulmaz.

## Birden çok parçayı aynı anda seçip silme

Kitaplığın parça listesinde her parçada bir onay kutusu ve geçerli filtreyle eşleşen tüm parçaları seçen bir **Tümünü seç** kutusu vardır ([Kitaplık sayfası](library-catalog.md#library-page)na bakın). Seçim çubuğundaki **Kitaplıktan sil**, hepsini tek bir istekte kaldırır (`DELETE /delete/batch`, [API başvurusu](../api-reference.md)na bakın); bir parçayı tek tek silmekle aynı parça başına temizlikle (`.lrc`, sahipsiz `cover.jpg`, boş klasörler).

Bir albümün veya çalma listesinin tamamını silmek için onu açın ve **⋯** menüsünden **Sil**’i seçin. Bir sanatçının her şeyi için, parça listesinin filtresine sanatçının adını yazın, ardından **Tümünü seç**’i seçip silin.
