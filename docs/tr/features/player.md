---
icon: lucide/headphones
---

# Yerleşik oynatıcı

Downtify, indirdiğiniz müziği ayrı bir uygulama olmadan dinleyebilmeniz için bir web oynatıcıyla gelir. Kitaplıktaki herhangi bir parça, albüm, sanatçı veya çalma listesinde — ya da Kuyruktaki tamamlanmış bir indirmede — oynat’a basın, oynatıcı başlar.

## Oynatıcı çubuğu

Bir parça yüklüyken her sayfanın altında bir oynatıcı çubuğu süzülür: kapak, başlık ve sanatçı, karıştır, önceki, oynat/duraklat, sonraki, tekrarla, geçen/toplam süre ve sözler ile sıradakiler panellerine kısayollar (sözler paneli [gizlenebilir](#hiding-the-lyrics)). Geniş ekranlarda ayrıca bir ses kaydırıcısı ve üst kenarı boyunca bir arama çubuğu vardır; telefonda temel öğelere indirgenir ve ince bir ilerleme çizgisi gösterir.

Başlığın yanında [şarkıyı beğenmek](liked-songs.md) için bir kalp vardır; telefon, başlığa yer kalsın diye onu çubuktan çıkarır, onun yerine **Şimdi çalıyor** içinde ve parça listelerinde tutar.

**Şimdi çalıyor**’u açmak için başlığa veya kapağa ya da genişlet düğmesine tıklayın.

## Şimdi çalıyor

Geçerli albüm kapağından alınan renklerle tonlanmış tam ekran bir görünüm:

- **Büyük kapak**, başlık ve sanatçı (o sanatçıya, albüme veya çalma listesine gitmek için sanatçıya ya da *Çalındığı yer* etiketine tıklayın), başlığın yanında [şarkıyı beğenmek](liked-songs.md) için bir kalp. Kapak ve sözler pencereyle birlikte küçülür — yalnızca yüksekliğini değiştirdiğinizde bile — böylece başlığın altında kalırlar.
- **Arama çubuğu** — tıklayın veya sürükleyin, odaktayken ok tuşlarını kullanın. Bir parça çalarken, albüm kapağından alınan renklerde yumuşak dalgalar çalınan kısmın üzerinde süzülür; duraklatıldığında düzleşir ve sisteminiz azaltılmış hareket istiyorsa sabit kalır
- **Oynatma denetimleri** — karıştır, önceki, oynat/duraklat, sonraki, tekrarla (kapalı → tümünü tekrarla → birini tekrarla)
- **Ses** ve sessize alma düğmesi; oturumlar arasında kaydedilir. Seviyeyi donanım düğmelerinin denetlediği telefonda gizlidir
- **Uyku zamanlayıcısı** — oynatmayı 15, 30, 45, 60 veya 90 dakika sonra ya da geçerli parçanın sonunda durdurur. Kalan süre zamanlayıcı düğmesinin yanında görünür
- **Dosya bilgisi** — çalan dosyanın biçimi ve boyutu

Dört panel geniş ekranlarda kapağın yanında yer alır, telefonda onun yerini alır:

- **Şarkı sözleri** — zamanlamalı sözler geçerli satırı vurgular ve şarkıyla kayar; oraya atlamak için bir satıra tıklayın. Düz sözler olduğu gibi gösterilir. Sözler, parçanın yanındaki `.lrc` dosyasından ya da etiketlerine gömülü olanlardan gelir — bkz. [Şarkı sözleri](lyrics.md). Bu paneli gizleyebilirsiniz — bkz. [Sözleri gizleme](#hiding-the-lyrics).
- **Sıradaki** — oynatma kuyruğu. Parçaları yeniden sıralamak için sürükleyin, tek tek parçaları kaldırın ya da geçerli parçadan sonraki her şeyi temizleyin.
- **Ayrıntılar** — başlık, sanatçı, albüm, parça numarası, yıl, uzunluk, biçim, boyut, eklenme tarihi ve dosya yolu.
- **Ekolayzır** — sesi on frekans bandıyla şekillendirin; bkz. [Ekolayzır](#equalizer).

Şimdi çalıyor, sayfa adresinin bir parçasıdır (`?np=1`, ayrıca `&panel=lyrics|queue|details|equalizer`); böylece tarayıcının Geri düğmesi onu kapatır ve yeniden yükleme açık tutar.

## Sözleri gizleme

Kapağı ve kuyruğu sözler olmadan mı tercih edersiniz? **Ayarlar → Genel → Oynatıcı → Oynatıcıda şarkı sözlerini göster**’i kapatın. Hemen uygulanır ve oynatıcıda sözlere götüren her şeyi kaldırır:

- **Şarkı sözleri** paneli ve sekmesi (telefonda, Şimdi çalıyor alt kısmındaki düğmesi);
- oynatıcı çubuğundaki söz düğmesi;
- kısayol listesinden (`?`) de kaldırılan `L` kısayolu.

Şimdi çalıyor bunun yerine **Sıradaki**’nde açılır. Kapatmadan önceki bir `&panel=lyrics` bağlantısı da boş bir sekme yerine oraya düşer. Sözler gizliyken oynatıcı bir parçanın sözlerini hiç istemez.

::: info Gizlemek silmek değildir
Bu yalnızca oynatıcının gösterdiğini değiştirir. Dosyalarınız Downtify’ın içlerine gömdüğü sözleri korur ve yanlarındaki `.lrc` dosyaları yerinde kalır; böylece medya sunucuları ve diğer oynatıcılar onları yine görür. İndirmeler de söz getirmeye devam eder — bu, **Etiketler ve sözler** altındaki ayrı **Şarkı sözlerini indir** ayarıdır (bkz. [Şarkı sözleri](lyrics.md)).
:::

Tema ve ekolayzır gibi bu seçim de tarayıcıda (`localStorage`) saklanır; yani cihaz ve tarayıcı başınadır, Downtify sunucusu başına değil — sözleri telefonda gizleyip bilgisayarda açık tutabilirsiniz.

## Ekolayzır

Şimdi çalıyor’un **Ekolayzır** panelinde (veya `E`’ye basın) on bantlı grafik bir ekolayzır. **Deneysel** olarak işaretlidir: hâlâ değişebilir ve bazı tarayıcılarda sorun çıkarabilir (bkz. [Tarayıcı desteği](#browser-support)).

- 31, 62, 125, 250, 500 Hz ve 1, 2, 4, 8, 16 kHz’de **bantlar**, her biri 0,5 dB adımlarla ±12 dB. 31 Hz ve 16 kHz bantları shelf’tir; yani altındaki / üstündeki her şeyi de yükseltir veya keser. Bir bandı sürükleyin ya da odaklanıp ok tuşlarını kullanın (1 dB için `Page Up`/`Page Down`, sınırlar için `Home`/`End`); çift tıklama onu 0’a sıfırlar.
- **Hazır ayarlar** — Düz, Bas güçlendirme, Tiz güçlendirme, Vokal, Rock, Elektronik ve Akustik. Sonra herhangi bir bandı oynatmak hazır ayarı **Özel**’e çevirir.
- **Ön amfi** — her şeyin üstüne ±12 dB.
- **Açma/kapama anahtarı** ve **Sıfırla** (Düz’e, ön amfi 0’a, kapalıya döner). Bir bandı oynatmak veya bir hazır ayar seçmek ekolayzırı da açar.
- Kaydırıcıların arkasındaki eğri, tüm bantların birleşik yanıtıdır.

Bantları yükseltmek yüksek sesli müziği tam ölçeğin ötesine iter ve bozar; bu yüzden Downtify sesi eğrinin en yüksek güçlendirmesi kadar otomatik olarak düşürür — panel ne kadar olduğunu söyler. Bu tepeyi 0 dB’de tutar, böylece güçlendirilmiş bir hazır ayar sesi yalnızca yükseltmek yerine yeniden şekillendirir. Ön amfiyi 0 dB’nin üzerine çıkarmak bu güvenlik payını kaldırır ve panel yüksek bölümlerin bozulabileceği uyarısını verir.

Ayarlar tarayıcıda (`localStorage`) saklanır ve siz değiştirene kadar çaldığınız her şeye, her sekmede uygulanır. Tarayıcı başınadır, Downtify sunucusu başına değil.

### Tarayıcı desteği

Ekolayzır, tüm güncel tarayıcılarda bulunan Web Audio API’yi kullanır. Siz açana kadar oynatma Web Audio’ya hiç dokunmaz. Açıldıktan sonra ziyaretin geri kalanındaki ses ondan geçer — kapatmak yalnızca tüm bantları düzleştirir.

::: warning iPhone ve iPad’de Safari
iOS, ekran kilitlendiğinde ya da uygulama değiştirdiğinizde Web Audio’yu duraklatabilir; bu, ekolayzır açıkken oynatmayı durdurur. Ekran kapalıyken dinliyorsanız ekolayzırı kapatın ve sayfayı yeniden yükleyin.
:::

## Kuyruğu oluşturma

Bir albüm, sanatçı, çalma listesi veya parça listesini çalmak, o parçaları seçtiğinizden başlayarak sırayla kuyruğa alır. Bir koleksiyonda **Karıştır** onu rastgele sırayla başlatır. İndirmediğiniz parçalar doğrudan kuyrukta tam olarak çalar ve sunucunun akış önbelleğinden sunulur: biri çalarken sonraki zaten bir parça önceden hazırlanır; böylece oynatma indirilmemiş satırların arasından durmadan geçer — tarayıcının kendisinin YouTube’a ulaşamadığı yerlerde bile. Akıtılan bir parça asla kaydedilmez, beğenilmez veya yeniden yüklemeler arasında hatırlanmaz.

Her parçanın menüsünde (**⋯** düğmesi veya masaüstünde sağ tık) şunlar vardır:

- **Sıradaki olarak çal** — geçerli parçanın hemen ardına ekle
- **Kuyruğa ekle** — sona ekle
- **Albüme git** / **Sanatçıya git**
- **Bu cihaza kaydet** — dosyayı tarayıcı üzerinden indir
- **Kitaplıktan sil**

Aynı eylemler Kitaplıktaki çok parçalı bir seçim için de geçerlidir.

Kuyruk, geçerli parça, konumu, karıştır ve tekrarla hatırlanır; böylece Downtify’ı yeniden açmak kaldığınız yerden sürdürür (2000’den fazla parçalık kuyruklar hatırlanmaz). Silinen dosyalar kuyruktan otomatik olarak düşer.

## Klavye ve medya tuşları

| Tuş | Eylem |
|-----|--------|
| `Space` | Oynat / duraklat |
| `←` / `→` | 5 saniye ileri/geri sar |
| `Shift` + `←` / `→` | Önceki / sonraki parça |
| `↑` / `↓` | Ses |
| `M` | Sessiz |
| `S` | Karıştır |
| `R` | Tekrarla |
| `L` | Sözleri aç ([gizlenmedikçe](#hiding-the-lyrics)) |
| `Q` | Sıradakini aç |
| `E` | Ekolayzırı aç |
| `Ctrl` / `⌘` + `K` veya `/` | Ara |
| `G` sonra `L` / `D` | Kitaplığa / kuyruğa git |
| `Esc` | Şimdi çalıyor’u kapat |
| `?` | Tüm kısayolları göster |

Kısayollar bir alana yazarken ya da bir iletişim kutusu açıkken yok sayılır.

Oynatıcı geçerli parçayı işletim sistemine de bildirir (Media Session); böylece kilit ekranı denetimleri, kulaklık düğmeleri ve klavye medya tuşları çalışır, sistem destekliyorsa kapak da gösterilir.

## Nasıl çalışır

Parçalar, her dosyanın etiketlerinden başlık, sanatçı, albüm, parça numarası, yıl ve uzunluğu okuyan kitaplık listesinden (`GET /tracks`) gelir. Dosyalar `/downloads` statik bağlama noktasından sunulur; [yerinde bırakılan](slskd-navidrome.md#leave-files-in-place) slskd indirmeleri `/media/slskd/…` üzerinden çalınır. Kapak `/cover`’dan, sözler `/lyrics`’ten gelir — bkz. [API başvurusu](../api-reference.md#file-management).

Oynatma tarayıcının yerel HTML5 sesini kullanır. Eklenti yok, ek işlem yok.

## Desteklenen biçimler

Oynatıcı, tarayıcınızın HTML5 ses motorunun desteklediği her biçimi çalabilir. Bu genellikle tüm modern tarayıcılarda MP3, M4A/AAC, OGG ve OPUS’u kapsar. FLAC desteği değişir — Chrome ve Edge yerel olarak destekler; Firefox ve Safari desteklemeyebilir.
