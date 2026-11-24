---
icon: lucide/folder-plus
---

# Mevcut müzik klasörleri

Downtify’ın Kitaplığı, indirdiği dosyalardan ve işaret ettiğiniz **ek klasörlerden** oluşur. Bu klasörler `/downloads` içine kopyalanmaz. Downtify her dosyanın etiketlerini (başlık, sanatçı, albüm, parça numarası, yıl) okur, zaten sahip olduğunuz şarkıları atlar ve geri kalanını Kitaplıkta ve oynatıcıda eşleşen sanatçının altına yerleştirir.

## Klasör ekleme

1. Ana makinedeki klasörü kapsayıcıya bağlayın (Docker). Ayarlar’a yazdığınız yol **kapsayıcının içindeki** yoldur; [slskd’nin indirme klasörü](slskd-navidrome.md) ile aynı kural.
2. **Ayarlar → Kitaplık**’ı açın.
3. **Mevcut müzik klasörleri** altına bir veya daha fazla yol ekleyin (örneğin `/music/collection`). Alan yazdıkça dizinler önerir.
4. Henüz eşitlemeden saklamak istiyorsanız **Kaydet**’e, ya da **Klasörleri eşitle**’ye basın — bu, listeyi kaydeder ve hemen tarar.

```yaml
services:
  downtify:
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

Ayarlar’daki klasör o zaman `/music/collection` olur.

::: warning Dosyalar olduğu yerde kalır
Eşitleme dosyaları `/downloads` içine kopyalamaz. Klasör yazılabilir olduğunda, bu dosyalara bir indirmenin yazacağı ekstraları **yazar**: sözler (ve bir `.lrc` yan dosyası — dosyanın yanına ya da Ayarlar’da seçtiğiniz klasöre), dosyada yoksa bir kapak ve mümkünse iTunes’tan tür. Sonraki bir eşitleme, sözler etiketlerde olsa bile eksik bir yan dosyayı yazar ve kaynak dosya yazılabilirse mevcut bir `.lrc` dosyasını Ayarlar’da şu anda seçili konuma **taşır**. Kitaplıktan bir parçayı silmek yine diskteki o dosyayı siler.
:::

::: tip Salt okunur bağlamalar
Downtify’ın MP3’leri yeniden yazmasını istemiyorsanız koleksiyonu `:ro` ile bağlayın. Eşitleme yine de onları dizinler. `.lrc` dosyalarını [söz klasörüne](lyrics.md#sidecar-lrc-file) koyun (**.lrc dosyasını sesin yanında tut**’u kapatın). Eksik kapaklar MP3’e değil `/data/cover_cache` altına (Kitaplığın kapak uç noktası) kaydedilir. iTunes türü dosyaya değil, Downtify’ın kitaplık meta veri veritabanına kaydedilir. Salt okunur bir dosyanın yanında zaten duran bir `.lrc` söz klasörüne **kopyalanır** ve yerinde bırakılır.
:::

## Eşitleme ne yapar

1. Yapılandırılmış her klasörde çalınabilir ses arar (kitaplığın geri kalanıyla aynı biçimler: MP3, M4A, FLAC, OGG, WAV, AAC, OPUS).
2. Gömülü etiketleri okur. Başlığı/sanatçısı olmayan dosya, diğer kitaplık satırları gibi dosya adındaki `Sanatçı - Başlık`’a başvurur.
3. Kitaplık o şarkıya zaten sahipse dosyayı **atlar** (aynı sanatçı + başlık ve ikisi de biliniyorsa birkaç saniye içinde süre) — Downtify indirmiş olsun ya da başka bir ek klasörden gelmiş olsun.
4. **Sanatçıları eşleştirir**: kitaplıkta zaten bulunan adlarla (`The Beatles` ve `Beatles` tek sanatçı olur). Bilinen bir sanatçıyla eşleşmeyen adlar yeni sanatçı olarak görünür. Yeni sanatçılar, tamamlanmış bir indirmeyle aynı profil doldurma için (bu ayarlar açıksa fotoğraf/biyografi) kuyruğa alınır.
5. Klasör yazılabilirse **bir indirme gibi etiketler**. İçe aktarılan her parça için bir indirmenin kullanacağı aynı söz sağlayıcılarını, kapak aramasını (yalnızca dosyada görsel yoksa) ve iTunes tür aramasını kullanır. Sözler dosyaya gider; bir `.lrc` yan dosyası sesin yanına ya da Ayarlar’da seçtiğiniz [söz klasörüne](lyrics.md#sidecar-lrc-file) yazılır. Kapak ve tür [İndirme ayarları](download-settings.md)’nı izler (`download_cover_art`, `download_lyrics`). **Salt okunur** bir bağlamada MP3 yeniden yazılmaz: eksik kapak `/data/cover_cache` altında saklanır, tür kitaplık kataloğunda saklanır ve bir tane seçtiyseniz `.lrc` dosyaları söz klasörüne gider. Aramalar **Eşzamanlı indirmeler** boyutundaki gruplar halinde çalışır; Ayarlar → İndirmeler ve dosyalar’daki **Eşitleme araması arası bekleme** bu gruplar arasında bekler, böylece büyük klasörler sağlayıcıların hız sınırlarına takılmaz.
6. Kitaplık sayfası ve oynatıcı sonucu olağan kısa tarama TTL’ini beklemeden görsün diye kitaplık yol önbelleğini geçersiz kılar.

Eşitleme **arka planda** çalışır. Ayarlar’dan çıkabilirsiniz; hâlâ çalışırken geri dönmek eşitlemenin sürdüğünü gösterir. Bittiğinde Ayarlar **son eşitleme günlüğünü** (içe aktarılan / yinelenen / hata, ayrıca söz/kapak notları) gösterir.

Bu klasörlere daha fazla dosya bıraktıktan sonra **Klasörleri eşitle**’yi yeniden çalıştırın. Klasör listesini eşitlemeden kaydetmek de onları bir sonraki kitaplık taramasına (yaklaşık bir dakika ya da bir sonraki indirme/silme) dahil eder.

Bir klasörü listeden kaldırmak onun **eşlemesini kaldırır**: o parçalar Kitaplıktan ve oynatıcıdan çıkar, Downtify’ın ürettiği ekstralar (`.lrc` yan dosyaları, önbelleğe alınmış kapaklar) silinir. Diskteki ses dosyaları yerinde kalır.

Var olmayan veya okunamayan klasörler eşitlemeden sonra bildirilir; diğerleri yine de taranır.

## Yeni indirmeleri kitaplığınızdan ayrı tutun

Bazıları yeni şarkıların önce bir *gelen* klasörüne düşmesini, etiketlerini düzeltip yeniden adlandırdıktan ya da sıraladıktan sonra asıl müzik koleksiyonlarına taşınmasını ister. Bir [izleme](playlist-monitor.md) yine de bu koleksiyonda ne olduğunu bilmelidir; yoksa her şeyi yeniden indirir. Mevcut müzik klasörleri bunu sağlar:

1. Koleksiyonunuzu buraya ekleyin (`:ro` olarak bağlamak sorun değil) ve **Klasörleri eşitle** düğmesine basın. Yeni şarkılar yine indirme klasörüne gelir.
2. **Ayarlar → İndirmeler ve dosyalar** bölümünde [Dosya varsa yeniden indir](download-settings.md#overwrite-existing-files) seçeneğini kapatın.
3. Çalma listelerini her zamanki gibi izleyin. Koleksiyonunuzda zaten olan bir şarkı indirilmek yerine listeye bağlanır ve izlemenin sayfasında **Zaten kitaplıkta** olarak sayılır. Yalnızca eksik olanlar indirme klasörüne gelir.
4. Yeni dosyaları düzenleyin ve istediğiniz zaman koleksiyonunuza taşıyın. Saatlik kontrol indirme klasöründen ayrıldıklarını fark eder; izlemenin bir sonraki kontrolü onları koleksiyonda bulur (aynı ISRC ya da aynı sanatçı, başlık ve süre) ve ikinci kez indirmek yerine yeniden bağlar. Dosyaları yeniden adlandırmak, türleri değiştirmek ya da klasörleri taşımak sorun değil; sanatçıyı ve başlığı tanınır tutun.

Çalma listesinin M3U dosyası, Kitaplıktaki kaydı ve Navidrome listesi şarkılarını her iki yerden de listeler; böylece izleme yine eksiksiz bir liste oluşturur. Listeden ayrılan bir şarkı asla sizin yerinize silinmez: bkz. [Bir çalma listesinden ayrılan şarkılara ne olur](playlist-monitor.md#what-happens-to-songs-that-leave-a-playlist).

## Kitaplık yolları

Ek klasör dosyaları `ext/<id>/…` biçiminde sanal bir yol kullanır (id klasör yolunun özetidir, böylece liste yeniden sıralanabilir). Oynatıcı ve `GET /media/…` bu yolu kullanır; yerinde bırakılan Soulseek dosyaları için `slskd/…` gibi.

Zaten `/downloads` (veya slskd kaynak klasörü) **içinde** duran bir klasör burada yok sayılır — o ağaç zaten kitaplıktır.

## API

| Yöntem | Yol                           | Açıklama                                                                         |
| ------ | ----------------------------- | -------------------------------------------------------------------------------- |
| `POST` | `/api/library/external/sync`  | Arka planda tarama başlatır. İsteğe bağlı `{folders: ["/path", …]}` gövdesi önce kaydedilir. |
| `GET`  | `/api/library/external/sync`  | Çalışan iş ya da son biten günlük.                                               |
| `POST` | `/api/library/external/unmap` | Sesi silmeden bir klasörü kitaplıktan çıkarır.                                   |

Yanıt biçimi için [API başvurusu](../api-reference.md#post-apilibraryexternalsync)na bakın.

## Birincil kitaplık klasörü

Kayıtlı harici klasörlerden birini tercih etmek için **Ayarlar → Kitaplık → Primary library folder**’ı seçin.
Varsayılan, mevcut davranışı korur.
Eşleşen sanatçı, tam başlık (sürüm dahil) ve albüm gerekir;
bilinmeyen meta veri başka bir dosyayı gizlemez. Seçilen bir kaynak,
diğer kopyası klip girişleri veya çıkışları içeren bir kaydı temsil edebilir.

Bu bir listeleme tercihidir, taşıma değildir. Kaynak dosyalar, saklanan çalma listesi yolları,
sahiplik, beğeniler ve görünürlük kuralları yeniden yazılmaz ya da silinmez.
Çalma listesi rozetleri gösterilen temsilcide birleştirilir; açıkça kaydedilmiş çalma listeleri
özgün yollarını çalmaya devam eder. Seçilen klasördeki farklı albümler ve sürümler
ayrı kalır. Boş veya kullanılamayan bir klasör kitaplığın geri kalanına döner.
Kaldırmak tercihi sıfırlar.
