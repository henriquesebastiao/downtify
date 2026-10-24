---
icon: lucide/library
---

# Kitaplık kataloğu ve yol eşitleme

Downtify, `/downloads` altındaki dosyaların (slskd klasörü — [slskd dosyaları yerinde bırakıldığında](slskd-navidrome.md#leave-files-in-place) — ve Ayarlar’da eklediğiniz [ek klasörler](external-library.md)) küçük bir **kataloğunu** tutar; böylece dosyalar taşındığında ya da çalma listeleri büyüdüğünde Kitaplık sayfası, oynatıcı, M3U dışa aktarma, Navidrome eşitleme ve yinelenen algılama tutarlı kalır.

## Neler saklanır

| Depo | Konum | Amaç |
|-------|----------|---------|
| **Parça dizini** | `/data/downtify_library.db` | Spotify parça kimliklerini kitaplık yollarıyla eşler; böylece diskte zaten olan bir parça tanınabilir |
| **Çalma listesi kataloğu** | `/data/downtify_library.db` | İndirilen her Spotify çalma listesine hangi parçaların ait olduğu |
| **Çalma listesi indirmeleri** | `/data/downtify_library.db` | İzlenen Spotify çalma listesi indirmeleri ve Spotify parça listelerinin önbelleği |
| **Navidrome dizini** | `/data/downtify_library.db` | Dosya başına Navidrome şarkı kimlikleri |
| **Kitaplık üst veri önbelleği** | `/data/downtify_library.db` | `GET /tracks` için dosya başına başlık, sanatçı, albüm, albüm sanatçısı, parça numarası, yıl, uzunluk ve kapak boyutu; yalnızca bir dosyanın değişiklik zamanı veya boyutu değişince yeniden okunur |
| **İyileştirme çalıştırmaları** | `/data/downtify_library.db` | [Kitaplığı iyileştir](library-upgrade.md) kuyruğu ve her parçanın en son ne zaman denetlendiği; böylece bir çalıştırma yeniden başlatmadan sağ çıkar |
| **Yol tarama önbelleği** | RAM, artı `/data/downtify_library.db` içinde bir anlık görüntü | `GET /tracks`’in katlanmış satırları, çalma listesi listeleri ve yol çiftleri. Arayüz rotaları bu anlık görüntüyü diski gezmeden sunar. Biten her indirme **anında anlık görüntüye eklenir** (yeni bir sanatçı beklemeden görünsün diye). Bir silme **bu dosyaları anında anlık görüntüden düşürür** (bir albüm beklemeden ızgaradan kaybolsun diye). Tüm ağacın tam taraması, indirme kuyruğu boşa çıktıktan birkaç saniye sonra arka planda çalışır — sabit bir zamanlayıcıyla değil. `GET /list?refresh=true` anlık görüntüyü bırakır ve şimdi yeniden tarar. |
| **Gizlenen öğeler** | `/data/downtify_library.db` | Bir yöneticinin [kullanıcılardan gizlediği](users.md#hiding-from-users) şarkılar, albümler ve sanatçılar |
| **Kapak önbelleği** | `/data/cover_cache` (isteğe bağlı) | `GET /cover` için çıkarılmış kapak görselleri |

Dosyalar taşımalar boyunca bir **içerik anahtarıyla** eşleştirilir — dosyanın adı ve boyutunun bir hash’i. Bir dosyayı başka bir klasöre taşımak anahtarını korur; onu farklı bir dosyayla değiştirmek ona yeni bir anahtar verir.

## Ayarlar → Kitaplık

### Kapakları diskte önbelleğe al

Açıkken Downtify çıkarılmış kapak görsellerini `/data/cover_cache` altında tutar; böylece Kitaplık ve oynatıcı her küçük resim için etiketleri yeniden okumaz. İstediğiniz zaman kapatılabilir; yalnızca disk alanına mal olur.

### Kitaplık yollarını düzelt

Downtify dışında **diskte dosyaları taşıdıktan veya yeniden adlandırdıktan** ya da elle sildikten sonra kullanın.

1. **Ayarlar → Kitaplık → Kitaplık yollarını düzelt**’i açın.
2. Downtify kitaplık klasörlerini tarar ve:
    - bir dosya artık eskiden olduğu yerde değilken aynı dosya (aynı içerik anahtarı) başka yerde bulunursa parça dizininde ve çalma listesi kataloğunda **yolları günceller**;
    - artık var olmayan dosyaların **eskimiş girdilerini kaldırır**;
    - içerik anahtarları var olmadan önce saklanmış eski girdileri **dizinler**;
    - **[beğenilen şarkıları](liked-songs.md#keeping-likes-in-step-with-the-files)** yeni konumlarına **taşır**.
3. **M3U oluştur** ve/veya **Navidrome’da çalma listesi oluştur** etkinse, etkilenen çalma listeleri yeniden yazılır.

Yalnızca düğmeye bastığınızda (ya da `POST /api/library/reconcile` çağırdığınızda) çalışır — asla bir zamanlamayla.

### Mevcut müzik klasörleri

Downtify’ın indirmediği bir koleksiyonu çalmak için klasörleri **Ayarlar → Kitaplık**’a ekleyin ve **Klasörleri eşitle**’ye basın. Dosyalar diskte kalır; etiketler okunur ve sanatçılar eşleştirilir. Bkz. [Mevcut müzik klasörleri](external-library.md).

::: warning
Bir çalma listesini yeniden yazmak, etiketleri kayıtlı oldukları Spotify parçasıyla açıkça uyuşmayan kitaplık dosyalarını siler — bkz. [slskd ve Navidrome](slskd-navidrome.md#playlist-sync).
:::

::: info Silmeler ve taşımalar
**Kitaplık** sayfasından parça silmek zaten kataloğu temizler ve etkilenen M3U dosyalarını ve Navidrome çalma listelerini arka planda yeniden yazar; bu yüzden sonradan düzeltilecek bir şey yoktur.
:::

## Kitaplık sayfası

Kitaplık sayfasında dört sekme vardır — **Albümler**, **Sanatçılar**, **Çalma listeleri** ve **Parçalar**:

- **Albümler, sanatçılar ve çalma listeleri** kapak ızgarası veya kompakt liste olarak gösterilir (geçiş hatırlanır); metin süzgeci ve yakınlarda eklenen, ad, sanatçı, yıl veya parça sayısına göre sıralama vardır. Albümler ve sanatçılar her dosyanın etiketlerinden (albüm sanatçısı, albüm, yıl) oluşturulur; yani dosyaların diskte nasıl düzenlendiğine bağlı değildir. Albüm sanatçısı `Various Artists` olan bir parça sanatçı etiketine göre gruplanır; böylece `Zé Neto & Cristiano` gibi ikili adları o adın altında görünür. Albüm etiketi olmayan bir parça Albümler’de değil, Parçalar’da ve sanatçısının altında görünür.
- **Çalma listeleri**, bir [M3U dosyası](m3u-export.md) olan indirilmiş çalma listeleri, **Yeni çalma listesi** ile oluşturduğunuz (düzenlenebilir) çalma listeleri ve henüz M3U’su olmayan izlenen [çalma listesi indirmeleridir](slskd-navidrome.md#playlist-downloads). İçe aktarılan Spotify/YouTube çalma listeleri, onları [ayırana](#detach-an-imported-playlist) kadar salt okunur kalır. Başkalarının [sizinle paylaştığı](users.md#sharing-playlists) çalma listeleri ızgaranın altında, sizinkilerden ayrı listelenir. Bir şarkıyı [beğendikten](liked-songs.md) sonra *Beğenilen şarkılar* en başta listelenir. Sizin oluşturduğunuz bir çalma listesi en fazla dört parça kapağından oluşan bir mozaik kullanır; içe aktarılanlar M3U ile birlikte kaydedilen görseli korur.
- **Parçalar**, metin süzgeci, biçim süzgeci ve onay kutuları olan sıralanabilir bir tablodur (başlık, albüm, biçim, eklenme tarihi, uzunluk) — birine tıklayın, sonra bir aralık seçmek için Shift ile başka birine tıklayın. Bir sütun başlığına tıklayarak ya da tablonun üstündeki **Sırala** menüsüyle sıralayın (başlıkların gizli olduğu telefonda tek yol): yakınlarda eklenen veya en eski önce, başlık, sanatçı veya albüm A–Z ya da Z–A, en uzun veya en kısa önce. Seçim hatırlanır.

Bir çalma listesinin şarkıları aynı **Sırala** menüsüne sahiptir; seçeneklere **Çalma listesi sırası** (çalma listesinin kendi sırası, başladığı yer) eklenir; bir sütun başlığına tıklamak da çalışır. **Çal** ve şarkı listesi seçtiğiniz sırayı izler ve seçim her çalma listesi için hatırlanır.

Bir albüm, sanatçı veya çalma listesini açmak parçalarını **Çal**, **Karıştır**, **Kuyruğa ekle** ve **ZIP olarak indir** ile gösterir. Sizin oluşturduğunuz bir çalma listesinde ayrıca **Şarkı ekle**, **Yeniden adlandır** ve **Paylaş…** vardır (bkz. [çalma listelerini paylaşma](users.md#sharing-playlists)); içe aktarılanda **Paylaş…** ve **Kaynaktan ayır** (aşağıda) vardır; indirilmiş bir çalma listesi sayfası kaç parçasının indirildiğini gösterir, eksik olanları **Eksikleri indir** ile listeler ve **Yeni parçaları izle** sunar. **Çalma listesini sil** **⋯** menüsündedir: içe aktarılan çalma listeleri sesi siler; sizin oluşturduğunuz bir çalma listesi yalnızca çalma listesini kaldırır.

### İçe aktarılan bir çalma listesini ayırma

Bir Spotify veya YouTube Music bağlantısından içe aktarılan bir çalma listesi düzenlenemez, çünkü Downtify onu kaynağıyla eşzamanlı tutar. Birini toparlamak için — ait olmayan bir şarkıyı atmak, ait olan birini eklemek — açın ve **Kaynaktan ayır**’ı seçin. Oluşturduklarınız gibi bir çalma listesi olur: şarkıları ve sahibi olduğu gibi kalır ve **Şarkı ekle**, **Yeniden adlandır** ve şarkı kaldırma elde edersiniz. Karşılığında kaynağıyla bağ kesilir: artık Spotify veya YouTube Music’ten güncellenmez, [Çalma Listesi İzleyici](playlist-monitor.md) izlemesi (varsa) kaldırılır ve “eksik şarkılar” takibi gider. Zaten indirilmiş şarkılara asla dokunulmaz ve görseli ilk düzenlemenize kadar kalır; o zaman şarkılarının bir mozaiği onun yerine geçer. Ayırma uygulamadan geri alınamaz; bağlantıyı yeniden indirmek yeni bir içe aktarılmış çalma listesi oluşturur.

Her hesap aynı kitaplığı görür: bir yöneticinin [kullanıcılardan gizlediği](users.md#hiding-from-users) onlar için dışarıda kalır ve bir yönetici her şeyi, gizli olanın üstünde çizili bir gözle görür. Yöneticiler bir şarkının, albümün veya sanatçının `…` menüsünden ya da **Parçalar** içindeki seçim çubuğundan gizler ve gösterir.

**ZIP olarak indir**, seçili parçaları göz attığınız cihaza, klasör düzenini koruyarak tek bir ZIP olarak kaydeder — Downtify bir ev sunucusunda çalışırken ve bir grup parçayı yerelde istediğinizde kullanışlıdır. Geçerli süzgecin gösterdiği her şeyi almak için **Tümünü seç** ile birleştirin. Arşiv indirilirken oluşturulur; yani sunucunun diskine hiçbir şey yazılmaz ve indirme başına 2000 parçayla sınırlıdır.

## API

| Yöntem | Yol | Açıklama |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Yol tarama önbelleğini atlayarak kitaplık yolları |
| `GET` | `/api/library/summary` | Ana sayfa sayıları ve son albümler, tam parça listesi olmadan |
| `GET` | `/api/library/albums` | Albüm kutucukları (sayılar + kapak dosyası), her parça olmadan |
| `GET` | `/api/library/artists` | Kitaplık ve Keşfet için sanatçı kutucukları (sayılar + kapak dosyası) |
| `GET` `POST` | `/api/library/visibility` | Yöneticiler: kullanıcılardan neyin gizlendiği ve öğeleri gizle / göster |
| `POST` | `/api/library/lookup` | Zaten indirilmiş arama/bağlantı şarkıları için kitaplık satırları |
| `GET` | `/tracks` | Etiketli kitaplık parçaları. `?playlist=`, `?artist=`, `?album=`, `?q=` ve `?limit=` bir alt küme döndürür |
| `GET` | `/media/{path}` | `slskd/…` ve `ext/…` yolları dahil bir kitaplık dosyasını sunar |
| `GET` | `/playlist-cover?file=…` | Bir çalma listesinin kendi [kapağını](playlist-cover-art.md) sunar; `/playlists` tarafından `cover` olarak bildirilir |
| `POST` | `/api/library/archive` | Seçili parçaların bir ZIP’ini hazırlar (tek kullanımlık bir bilet döndürür) |
| `GET` | `/api/library/archive/{token}` | O ZIP’i tarayıcıya akıtır |
| `DELETE` | `/api/library/playlist?playlist_name=…` | İçe aktarılan bir çalma listesinin parçalarını, M3U’sunu ve kataloğunu siler — ya da sizin oluşturduğunuz bir çalma listesinin yalnızca M3U’sunu |
| `POST` | `/api/library/playlists` | Boş, düzenlenebilir bir çalma listesi oluşturur |
| `POST` | `/api/library/playlists/tracks` | Sizin oluşturduğunuz bir çalma listesine kitaplık dosyaları ekler veya kaldırır |
| `POST` | `/api/library/playlists/rename` | Sizin oluşturduğunuz bir çalma listesini yeniden adlandırır |
| `PUT` | `/api/library/playlists/visibility` | Sahibi olduğunuz bir [çalma listesini paylaşır](users.md#sharing-playlists), salt görüntüleme |
| `POST` | `/api/library/playlists/copy` | Açabildiğiniz bir çalma listesinin kopyasını, düzenlenebilir kendi çalma listeniz olarak kaydeder |
| `POST` | `/api/library/playlists/detach` | İçe aktarılan bir çalma listesini düzenlenebilir hale getirir |
| `POST` | `/api/library/reconcile` | Kitaplık yollarını düzeltir, sonra M3U/Navidrome çalma listelerini yeniler |
| `POST` | `/api/library/external/sync` | Ek müzik klasörlerinin arka plan taramasını başlatır |
| `GET` | `/api/library/external/sync` | Çalışan ek klasör eşitlemesi veya son biten günlük |
| `POST` | `/api/library/external/unmap` | Ses silmeden bir ek klasörü kitaplıktan çıkarır |
| `GET`/`POST` | `/api/library/upgrade…` | Zaten indirilmiş olanı tarar ve onarır — bkz. [Kitaplığı iyileştir](library-upgrade.md#api) |

İstek ve yanıt biçimleri için [API başvurusuna](../api-reference.md#library) bakın.
