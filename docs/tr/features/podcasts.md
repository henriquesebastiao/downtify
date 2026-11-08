---
icon: lucide/mic
---

# Podcastler

Bir programa abone olun, yeni bölümleri kendiliğinden insin — her hafta bir bağlantıyı yeniden yapıştırmadan. Podcastler baştan sona müzikten farklı ele alınır: bir bölüm zaten bir RSS `<enclosure>` URL’sinde duran bitmiş bir ses dosyasıdır; dolayısıyla YouTube eşleştirmesi ya da dönüştürme yoktur, yalnızca bir indirme ve etiket yazımı vardır.

Kenar çubuğundan **Podcastler**’i açın (telefonda: **Daha fazla → Podcastler**).

Abonelikler abone olana aittir: her hesap kendi programlarını izler (aynı besleme iki kez abone olunursa iki klasöre düşer), kendi bölümleri, devam konumları ve gizlemeleriyle. Bir yönetici tüm abonelikleri görür.

## Abone olma

Bunlardan birini **Podcast ekle** kutusuna yapıştırın ya da aramak için bir ad yazın:

| Girdi | Ne olur |
|-------|--------------|
| Bir podcast’in RSS besleme URL’si | Doğrudan getirilir ve ayrıştırılır |
| Bir Spotify program bağlantısı (`open.spotify.com/show/…`) | Programın adı Spotify’dan okunur, sonra iTunes podcast dizini üzerinden herkese açık RSS beslemesiyle eşleştirilir |
| Bir Spotify bölüm bağlantısı (`open.spotify.com/episode/…`) | Program bağlantısıyla aynı; ve başlığı beslemede eşleştirilebiliyorsa o bölüm vurgulanır |
| Bir programın adı (serbest metin) | iTunes podcast dizininde aranır |

::: info Spotify’a özel programlar indirilemez
Yalnızca Spotify’da bulunan (herkese açık beslemesi olmayan) bir program öyle olarak bildirilir — Downtify tahmin yürütmez ya da başka bir şeye yönelmez. Özel olduğunu varsaymadan önce kontrol etmek için programı adıyla arayın.
:::

Onaylamadan önce şunları seçersiniz:

- **Sakla** — aşağıdaki [Kaç bölüm indirilir](#how-many-episodes-are-downloaded) bölümüne bakın.
- **Aralık** — beslemenin yeni bölümler için ne sıklıkla denetlendiği, her 15 dakikadan ayda bire kadar. Abonelikler, [Çalma Listesi İzleyici](playlist-monitor.md)’nin izlemeleriyle aynı takvimde ve aynı arka plan taramasıyla denetlenir — onun için yalnızca başka bir izleme türüdür.

## Kaç bölüm indirilir

**Sakla** ayarının, program başına bir kez seçilen iki ayrı davranışı vardır:

- **Her yeni bölüm** — hemen yalnızca en yeni tek bölümü indirir (abone olmak bir programın tüm eski kataloğunu çekme daveti değildir), sonra her denetimde ortaya çıkan yeni bölümleri indirir. Hiçbir şey otomatik olarak silinmez.
- **Son *N* bölüm** — kayan bir pencere. Her denetimden (ilki dahil) sonra en son yayımlanan *N* bölüm indirilir ve daha eski indirilmiş her bölüm yer açmak için kaldırılır. *N*’i sonradan artırmak, kaldırılan bu bölümleri yeniden indirilebilir yapar; **İndirmeyi kaldır** ile kendinizin kaldırdığı bir bölüm bu yolla asla geri getirilmez — bkz. [Bölümleri kaldırma](#removing-episodes).

**Sakla** ve aralığı dilediğiniz zaman programın sayfasından değiştirin.

## Bölümler

Bir programın sayfası bölümlerini en yeniden eskiye listeler; her birinde yayın tarihi ve süre vardır. Saklama ilkesinin kapsamadığı bir bölüm de burada görünür — ne kadar eski olursa olsun yalnızca onu almak için **İndir**’e dokunun.

### Bölümleri kaldırma

Her bölümün **⋯** menüsünde **İndirmeyi kaldır** vardır; dosyayı siler ama bölümü listede tutar. Bir bölümün dosyasının gitmesinin, farklı sonuçlar veren iki yolu vardır:

| Nasıl | Otomatik geri gelir mi? |
|-----|----|
| Saklama onu dışarı attı (“son N’i sakla” penceresinin dışında kalan daha eski bir bölüm) | Evet, **Sakla**’yı yeniden artırırsanız |
| **İndirmeyi kaldır**’ı siz seçtiniz | Hayır — dilediğiniz zaman elle yeniden indirin |

### Oynatıldı olarak işaretleme

Bir bölümü elle oynatıldı veya oynatılmadı olarak işaretlemek için **⋯** menüsünü kullanın ya da sadece sonuna kadar çalmasına izin verin — uzunluğunun son birkaç saniyesindeki bir bölüm kendiliğinden oynatıldı olarak işaretlenir.

## Bölümleri oynatma

Bölümler müzikle aynı yerleşik oynatıcıda çalar; yalnızca bir podcast bölümünde görünen birkaç farkla:

- Tek bir bölüm için geçerli olmayan karıştır ve tekrarla yerine **15 sn geri / 30 sn ileri**.
- Uyku zamanlayıcısının yanında **oynatma hızı** (0,75× – 2×).
- **Devam konumu** her ~10 saniyelik oynatmada ve duraklattığınızda bir kez daha sunucuya kaydedilir; böylece sekmeyi kapatmak — ya da Downtify’ı başka bir cihazda açmak — bölümü bıraktığınız yere yakın yerden sürdürür. Bir programın bölüm listesi, yarıda kalan her şey için “… konumundan devam et” ipucu gösterir.

Kalp (beğenilen şarkılar) ve “albüme/sanatçıya git” bölümler için geçerli değildir ve birinde görünmez.

## Kitaplık

Podcastlerin kendi yeri vardır — **Kitaplık**’ta asla parça, albüm veya sanatçı olarak görünmezler ve bir [Kitaplığı iyileştir](library-upgrade.md) çalıştırması onlara tamamen dokunmaz (bir bölümün etiketlerinin yenileneceği bir Spotify parça kimliği ve aranacak ayrı sözleri yoktur).

Bölüm dosyaları yine aynı indirme birimi altında, `Podcasts/<Program>/<tarih> - <Bölüm>.<uzantı>` içinde durur; böylece kitaplığınıza yönlendirilmiş her medya sunucusu onları da görür.

## Etiketler

Downtify, podcast uygulamalarının ve medya sunucularının bir bölüm için zaten okuduğunu yazar: başlık, albüm olarak program, sanatçı olarak programın yazarı, yayın yılı, bölüm/sezon numaraları, programın kendi görseli (beslemenin kendi görseli ile iTunes’unkinden büyük olanı; [müzik kapakları](download-settings.md#cover-art-resolution) ile aynı fikir) ve yorum olarak bölüm açıklaması. Program notları düz metin olarak saklanır — Downtify HTML’i işlemek yerine ayıklar.

## Bilmekte fayda var

- **Video podcastleri yok.** Tek eki bir video dosyası olan bir bölüm tamamen atlanır; yalnızca ses desteklenir.
- **Bölüm işaretleri (chapters) yok.** Bölüm işaretleri içeren beslemelerde bunlar Downtify’da henüz yoktur.
- **Navidrome’a yansıtılmaz.** Çalma listelerinden farklı olarak podcast abonelikleri bir Navidrome kitaplığına itilmez — bölümler, medya sunucunuzun zaten kendi başına gördüğü düz dosyalardır.
- Aboneliği iptal etmek (**⋯ → Aboneliği iptal et**) varsayılan olarak indirilmiş bölümleri kaldırır; dosyaları yerinde bırakmak için **Aboneliği iptal et, indirilen bölümleri sakla**’yı seçin.

## API

`POST /api/podcasts/resolve`, `GET /api/podcasts/search`, `POST /api/podcasts/subscribe`, `GET/PATCH/DELETE /api/podcasts/shows/{id}`, `GET /api/podcasts/shows/{id}/episodes`, `POST /api/podcasts/episodes/{id}/download`, `DELETE /api/podcasts/episodes/{id}` ve `PUT /api/podcasts/episodes/{id}/playback`. [API başvurusuna](../api-reference.md#podcasts) bakın.
