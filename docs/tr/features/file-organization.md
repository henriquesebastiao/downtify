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

**Ayarlar → İndirmeler ve dosyalar → Sanatçıya göre düzenle** açıkken (varsayılan) çalma listesi ve albüm indirmeleri dahil her parça, ana sanatçının adını taşıyan bir alt klasörde toplanır:

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

## M3U ve sanatçı klasörleri

*Sanatçıya göre düzenle* açıkken M3U üretimi de açıkken bir Spotify çalma listesi indirirseniz M3U, çalma listesi alt klasörünün içine değil `<downloads>/Playlists/<çalma-listesi-adı>.m3u` yoluna konur. Bunun nedeni, parçaların artık birden çok sanatçı klasörüne dağılmış olmasıdır. M3U içindeki göreli yollar, kitaplığı nereye bağlarsanız bağlayın doğru çözülmeye devam eder.

## Ayarı değiştirme

Ayar, tüm **yeni** indirmeler için hemen etkili olur. Diskte zaten bulunan dosyalar taşınmaz.

## Bir parçayı silmek boş klasörleri temizler

Kitaplık sayfasından bir parçayı silmek, boşaldığı anda onun çalma listesi, sanatçı veya albüm klasörünü de kaldırır — ve artık boş kalan üst klasörlerden de yukarı doğru devam eder (örneğin son albümü gittikten sonra sanatçı klasörü), hiçbir zaman kaldırılmayan indirme dizininin kendisinde durur. İçinde başka bir şey bulunan klasöre — başka bir parça, bir `.m3u`, hâlâ kullanılan bir `cover.jpg` — dokunulmaz.

## Birden çok parçayı aynı anda seçip silme

Kitaplığın parça listesinde her parçada bir onay kutusu ve geçerli filtreyle eşleşen tüm parçaları seçen bir **Tümünü seç** kutusu vardır ([Kitaplık sayfası](library-catalog.md#library-page)na bakın). Seçim çubuğundaki **Kitaplıktan sil**, hepsini tek bir istekte kaldırır (`DELETE /delete/batch`, [API başvurusu](../api-reference.md)na bakın); bir parçayı tek tek silmekle aynı parça başına temizlikle (`.lrc`, sahipsiz `cover.jpg`, boş klasörler).

Bir albümün veya çalma listesinin tamamını silmek için onu açın ve **⋯** menüsünden **Sil**’i seçin. Bir sanatçının her şeyi için, parça listesinin filtresine sanatçının adını yazın, ardından **Tümünü seç**’i seçip silin.
