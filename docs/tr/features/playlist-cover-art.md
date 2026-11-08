---
icon: lucide/image
---

# Çalma listesi kapakları

Downtify, medya sunucuları ve dosya gezginlerinin genel bir simge yerine çalma listesinin gerçek görselini göstermesi için çalma listesinin kendi kapağını [M3U dosyasının](m3u-export.md) yanına kaydedebilir.

Varsayılan olarak açıktır. **Ayarlar → İndirmeler ve dosyalar → Çalma listesi kapağını kaydet** içinden kapatın.

## Dosya nereye gider

Kapak, **çalma listesinin M3U’suyla aynı adla ve aynı klasöre**, yalnızca `.jpg` uzantısıyla yazılır:

```
<downloads>/<çalma-listesi-adı>/<çalma-listesi-adı>.m3u
<downloads>/<çalma-listesi-adı>/<çalma-listesi-adı>.jpg
```

*Sanatçıya göre düzenle* veya *Albüme göre düzenle* açıkken parçalar sanatçı klasörlerine dağılır ve M3U merkezi bir `Playlists/` dizinine gider ([Dosya düzeni](file-organization.md) sayfasına bakın) — kapak da onu izler:

```
<downloads>/Playlists/<çalma-listesi-adı>.m3u
<downloads>/Playlists/<çalma-listesi-adı>.jpg
```

::: info M3U gerekir
**M3U çalma listeleri yaz** kapalıyken kapak da kaydedilmez: Downtify görseli M3U’nun yoluna göre yerleştirir, M3U yoksa koyacak yer yoktur. M3U yazımı kapalıyken ayar gizlenir.
:::

## Kaynaklar ve çözünürlük

| Kaynak | Çözünürlük |
|--------|-----------|
| **Spotify** | Herkese açık gömme sayfasının çalma listesi için sunduğu en büyük görsel — parçaların kapakları için zaten kullanılanla aynı |
| **YouTube Music** | Her zaman 1200×1200 istenir; yalnızca parça başına kapakları etkileyen [Kapak çözünürlüğü](download-settings.md#cover-art-resolution)’nden bağımsızdır |

İki hizmet de özgün görsel PNG olsa bile bu URL’ler için JPEG sunar; bu yüzden dosya her zaman `.jpg` olarak kaydedilir.

## Ne zaman indirilir

Her iki durumda da **parçalardan önce** — klasör dolarken zaten çalma listesine benzer ve indirmenin ortasında tarayan bir medya sunucusu çıplak bir klasör yerine görseli bulur:

- **Elle çalma listesi indirmesi** — çalma listesi adı çözümlenir çözümlenmez, ilk parça başlamadan önce bir kez.
- **[Çalma Listesi İzleyici](playlist-monitor.md)** — indirilecek bir şey bulan her tarama için, o taramanın ilk parçasından önce bir kez. Yeni bir şey bulmayan tarama onu yeniden almaz.

Kapağın çözümlenememesi veya indirilememesi (bir ağ hatası, görseli olmayan bir çalma listesi) günlüğe yazılır ve atlanır — indirmenin kendisini asla geciktirmez ya da başarısız kılmaz.

## Downtify arayüzünde

Kendi görseli olan bir çalma listesi (bir Spotify veya YouTube çalma listesiyle indirilen), Kitaplığın çalma listelerini listelediği her yerde onu gösterir — ızgara, çalma listesi sayfası, kenar çubuğu ve oynatıcı. Görseli olmayan çalma listeleri ve Kitaplıkta oluşturduğunuz çalma listeleri, en fazla dört farklı parça kapağından oluşan bir mozaik gösterir: ikisi yan yana, üçü solda uzun bir döşeme artı sağda üst üste iki, dördü 2×2 ızgara olarak. Aynı kolaj, Navidrome da görsün diye elle oluşturulan bir çalma listesinin M3U’sunun yanına `<çalma-listesi-adı>.jpg` olarak yazılır ve şarkı ekleyip çıkardıkça yeniden oluşturulur.

## Navidrome

Yapılandırılacak bir şey yok: Navidrome çalma listesi görselini bir **yan görselden** — çalma listesinin adını taşıyan, aynı klasördeki bir dosya — çözümler; Downtify’ın yazdığı da tam olarak budur. Navidrome’un müzik klasörü indirme klasörünüzü kapsadığı sürece görsel bir sonraki taramasında belirir. Downtify’dan hiçbir API çağrısı gerekmez. [slskd ve Navidrome](slskd-navidrome.md#navidrome) sayfasına bakın.

## Temizlik

Kitaplık sayfasından bir çalma listesini silmek, kapağını M3U’su ve parçalarıyla birlikte kaldırır — [Bir çalma listesini silme](slskd-navidrome.md#deleting-a-playlist) bölümüne bakın.
