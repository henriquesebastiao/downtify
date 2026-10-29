---
icon: lucide/import
---

# Kitaplığı içe aktarma (CSV)

Kitaplığınızı başka bir hizmetten zaten dışa aktardınız mı? Şarkıları tek tek eklemek yerine CSV’yi içe aktarın ve tüm parçaları tek seferde indirme kuyruğuna alın.

## Desteklenen dışa aktarıcılar

| Araç | Notlar |
|------|-------|
| [Soundiiz](https://soundiiz.com/) | |
| [TuneMyMusic](https://www.tunemymusic.com/) | |
| [Exportify](https://github.com/watsonbox/exportify) | |

Downtify hiçbir aracın tam sütun şemasını sabit olarak kodlamaz. Bunun yerine CSV’nin başlık satırını büyük/küçük harfe bakmadan bilinen takma adlarla eşleştirir (`Title` / `Track` / `Track Title` / `Track Name` / `Song` / …, `Artist` / `Artists` / `Artist Name` / `Artist Name(s)` / … ve `Album` / `Album Name` / `Album Title` / …); böylece üçünden herhangi birinin dışa aktarımı — ya da aynı sütun adlarını kullanan elle hazırlanmış bir CSV — hiçbir şeyi yeniden adlandırmadan çalışır.

Başlık ve sanatçı zorunludur. Albüm varsa okunur ve parçanın albüm adı olarak saklanır (Kuyruk, eşleştirme ve dosya etiketleri). Bazı dışa aktarıcıların eklediği diğer sütunlar (ISRC, Spotify parça URI’si, süre) yok sayılır. Her satır, serbest metin araması gibi YouTube Music üzerinden çözümlenir.

## Nasıl içe aktarılır

1. Ana sayfada arama kutusunun altındaki **CSV içe aktar (Soundiiz, Exportify…)**’a tıklayın.
2. Dışa aktardığınız `.csv` dosyasını seçin.

Dosya tamamen tarayıcınızda okunur ve sunucuya düz metin olarak gönderilir — başka hiçbir yere yüklenmez. Downtify onu ayrıştırır, tanınan her satırı kuyruğa alır ve ilerlemenin diğer tüm toplu indirmeler gibi WebSocket üzerinden aktığı İndirme Kuyruğu’na gelirsiniz.

İçe aktarılan toplu iş dosyanın adını alır (`.csv` olmadan adı) ve diğer çalma listesi indirmeleri gibi, bu ayar açıksa bir [M3U dosyası](m3u-export.md) alır.

## Sınırlar ve hata yönetimi

- Dosya başına en fazla **2.000 satır**. Daha büyük dışa aktarımları birden çok dosyaya bölün.
- Başlığı veya sanatçısı olmayan satırlar sessizce atlanır. Eksik bir albüm sütunu ya da boş bir albüm hücresi sorun değildir — YouTube Music albümü sonradan yine doldurabilir.
- Bir hücredeki birden çok sanatçı (`,` veya `;` ile ayrılmış) listeye bölünür.
- Başlık satırında tanınabilir bir başlık/sanatçı sütunu yoksa içe aktarmanın tamamı, bulunan sütunları sayan bir hatayla baştan reddedilir — hiçbir şey kuyruğa alınmaz.

## İstek sınırlarından kaçınma

Büyük bir kitaplığı içe aktarmak kısa sürede çok sayıda YouTube Music araması ve indirmesini kuyruğa alır; bu da hız sınırına takılmanın kolay bir yoludur. Büyük bir dosyayı içe aktarmadan önce Ayarlar’da **[Eşzamanlı indirmeler](download-settings.md#parallel-downloads)** değerini düşürmeyi ve **[İndirmeler arası bekleme](download-settings.md#delay-between-downloads)**’yi açmayı düşünün.

## API

Temel uç nokta için API başvurusunda [`POST /api/download/csv`](../api-reference.md#post-apidownloadcsv) bölümüne bakın.
