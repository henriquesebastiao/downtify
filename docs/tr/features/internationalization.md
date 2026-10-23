---
icon: lucide/languages
---

# Uluslararasılaştırma

Downtify iki bağımsız yerde çevrilir: **uygulama** (arayüzü) ve bu **belgeler**. İkisinin de varsayılan dili **İngilizce**dir; kutudan çıktığı gibi dokuz dil daha içerir.

## Dil değiştirme

### Uygulama

**Ayarlar → Dil**’e gidin ve tercih ettiğiniz dili seçin. Seçim tarayıcının `localStorage`’ında saklanır ve sayfa yenilenmeden anında uygulanır. Sayfa ayrıca her yüklemede ve her değiştirdiğinizde sunucuya da bildirir (`settings.json` içindeki `ui_language` girdisi, bkz. [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate)); böylece tarayıcı olmadan çalışan işler dilinizi bilir - bir sanatçının biyografisi, parçalarından biri indirmeyi bitirdiğinde arka planda getirilir ve o dilde gelir (bkz. [Bir indirme bittiğinde](artist-images.md#when-a-download-finishes)). Sizin yapacağınız bir şey yok: bu özellikten önce bir dil seçtiyseniz, Downtify’ı bir sonraki açışınızda alınır. Farklı dillere ayarlanmış birden çok tarayıcıyla, onu en son yükleyen ya da değiştiren kazanır.

### Belgeler

Belgeler, tarayıcınızın tercih ettiği dile çevrilmişse o dilde, aksi halde İngilizce açılır. Üst çubuğun sağındaki **dünya düğmesi** dili istediğiniz zaman değiştirir ve sizi aynı sayfada (ve bölümde) tutar. Seçiminiz tarayıcıda hatırlanır ve bundan sonra başka bir dil seçene kadar tarayıcının dilinin önüne geçer.

Henüz çevrilmemiş bir sayfa bir not ve İngilizce metni gösterir; böylece her dilde her sayfa her zaman vardır.

## Kullanılabilir diller

| Kod | Dil | Uygulama | Belgeler |
| ------- | ------------------ | --- | ---- |
| `en` | English (varsayılan) | ✓ | ✓ |
| `es` | Español | ✓ | ✓ |
| `pt-BR` | Português (Brasil) | ✓ | ✓ |
| `fr` | Français | ✓ | ✓ |
| `tr` | Türkçe | ✓ | ✓ |
| `el` | Ελληνικά | ✓ | ✓ |
| `hu` | Magyar | ✓ | ✓ |
| `bg` | Български | ✓ | ✓ |
| `de` | Deutsch | ✓ | ✓ |
| `ko` | 한국어 | ✓ | ✓ |

Geliştiriciler için hazırlanmış başvuru sayfaları — [API başvurusu](../api-reference.md), [mobil istemci sözleşmesi](../mobile-client-contract.md) ve değişiklik günlüğü — her dilde İngilizce kalır.

## Çeviri katkısı

Uygulamayı, belgeleri ya da ikisini birden çevirebilirsiniz. Bunlar ayrı dosyalarla ayrı işlerdir; yani bir pull request ikisinden birini içerebilir — ya da bir dil önce birine, sonra diğerine eklenebilir.

| Çevirdiğiniz | Dosyaların yeri | Ne zaman tamamlanır |
| ------------- | ------------------- | --------- |
| **Yalnızca uygulama** | `frontend/src/i18n/locales/<code>.js` | dil **Ayarlar → Dil** içinde göründüğünde |
| **Yalnızca belgeler** | `docs/.vitepress/locales/<code>.mjs` ve `docs/<code>/` içindeki Markdown sayfaları | dil belgelerin dünya menüsünde göründüğünde |
| **İkisi birden** | yukarıdakilerin hepsi | ikisi de |

Bir dilin belgelere eklenmesi için uygulamada var olması gerekmez, tersi de geçerlidir.

## Uygulamayı çevirme

Uygulamaya bir çeviri eklemek üç adımlı bir süreçtir:

### 1. İngilizce dil dosyasını kopyalayın

Dil dosyaları `frontend/src/i18n/locales/` içinde durur. Her dosya, anahtarları `en.js`’in yapısıyla eşleşen tek bir nesne dışa aktarır. Dosya adı için bir [IETF dil etiketi](https://en.wikipedia.org/wiki/IETF_language_tag) kullanın.

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/it.js
```

### 2. Değerleri çevirin

Anahtarları, yer tutucu belirteçleri (örn. `{count}`, `{name}`, `{file}`) ve genel biçimi değiştirmeyin — yalnızca sağ taraftaki dizeler değişmelidir. `language.name` değerini dilin **yerel** adına ayarlayın (`"Français"`, `"Deutsch"`, …) — dil seçicide gösterilen etiket budur.

### 3. Dili kaydedin

`frontend/src/i18n/index.js` içindeki `AVAILABLE_LOCALES`’e bir import ve bir girdi ekleyin:

```js
import it from './locales/it.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  // …
  { code: 'it', name: 'Italiano', messages: it }, // new
]
```

Frontend’i yeniden derleyin; diliniz **Ayarlar → Dil** içinde kendiliğinden görünür:

```bash
cd frontend && npm run build
```

### Uygulamayı çevirmek için ipuçları

- Eksik anahtarlar İngilizceye döner; bu yüzden kısmi çeviriler gayet iyi çalışır — elinizdekiyle bir PR gönderin.
- Bir sayıya bağlı dizeler çoğul biçimleri olan nesnelerdir, örn. `tracks: { one: '{count} track', other: '{count} tracks' }`. Biçim, dilinizin tarayıcıdaki [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) kuralıyla seçilir; bu yüzden diliniz hangi biçimleri kullanıyorsa onları ekleyin (`zero`, `one`, `two`, `few`, `many`, `other`) — `other` zorunludur. Sayılar dile göre otomatik biçimlendirilir.
- `{count}` veya `{file}` gibi yer tutucu belirteçler değişmeden kalmalıdır; çalışma zamanında yerine konurlar.
- Dizeleri kısa tutun — arayüz sıkı yerleştirilmiştir ve çok uzun çeviriler kötü kırılabilir.
- Çevirdikten sonra `frontend/` içinde `npm run dev` çalıştırın ve taşan ya da bağlamda tuhaf okunan bir şey olup olmadığını görmek için her sayfada kendi dilinizde gezinin.

## Belgeleri çevirme

Kaynak İngilizcedir: `docs/` içindedir. Diğer her dilin, kodunu taşıyan bir klasörü vardır (`docs/pt-BR/`); içinde İngilizceyle **aynı dosya adları** ve sitenin kendi metinleri için bir dosya bulunur (`docs/.vitepress/locales/pt-BR.mjs`: kenar çubuğu başlıkları, arama kutusu, alt bilgi, vurgu kutularının etiketleri). Henüz çevrilmemiş bir sayfa, bir not gösteren ve İngilizce sayfayı içeren küçük bir taslaktır.

### Mevcut bir dilin bir sayfasını çevirme

`docs/` içinden:

```bash
npm install
npm run i18n -- status pt-BR           # what is translated, what is English-only, what is out of date
npm run i18n -- start pt-BR features/users.md
```

`start`, `docs/pt-BR/features/users.md` taslağını İngilizce sayfanın bir kopyasıyla değiştirir. Onu yerinde çevirin, sonra denetleyin:

```bash
npm test             # the translated pages must keep the English page's structure
npm run dev          # read it in the browser, in your language
```

Sayfa iyi okunduğunda bir pull request açın; kısmi çalışma da memnuniyetle karşılanır — dokunmadığınız sayfalar basitçe İngilizce kalır.

### Belgelere bir dil ekleme

1. `docs/.vitepress/locales/en.mjs` dosyasını `docs/.vitepress/locales/<code>.mjs` olarak kopyalayın ve çevirin: yerel `name`, sitenin metinleri (`ui`), vurgu kutusu etiketleri (`containers`) ve kenar çubuğu başlıkları (`nav`).
2. Onu `docs/.vitepress/locales/index.mjs` içinde kaydedin.
3. Sayfaları yalnızca İngilizce taslaklar olarak oluşturun: `npm run i18n -- stubs <code>`.
4. Sayfaları tek tek `npm run i18n -- start <code> <page>` ile çevirin.

Dil, kaydedilir kaydedilmez dünya menüsünde ve tarayıcı dili algılamasında görünür.

### Nelerin korunacağı ve nelerin çevrileceği

- Metni, başlıkları, tablo hücrelerini, vurgu kutusu başlıklarını ve ana sayfanın front matter’ındaki `title`/`text` değerlerini **çevirin**.
- Kod bloklarını, satır içi `code`’u, URL’leri, ortam değişkenlerini, API yollarını ve alan adlarını, dosya ve klasör adlarını, front matter anahtarlarını ve `icon:` ile `link:` değerlerini **olduğu gibi tutun**. Bir kod bloğundaki yorumu çevirmek sorun değildir.
- **Bağlantılar**: İngilizce sayfanın göreli `.md` bağlantılarını (`[Şarkı sözleri](lyrics.md#sidecar-lrc-file)`) aynen koruyun. Yalnızca İngilizce olan bir sayfaya bağlantı hâlâ çalışır. Ana sayfada bağlantılar dil önekiyle yazılır (`/pt-BR/features/player/`).
- **Başlıklar**: Aynı başlıkları, aynı sırada ve aynı düzeylerde koruyun. Bir bölüme bağlantılar (`#sidecar-lrc-file`) her dilde çalışmaya devam eder, çünkü çevrilmiş sayfa İngilizce başlık kimliklerini yeniden kullanır — hiçbir zaman bir kimlik yazmaz ya da çevirmezsiniz.
- **Düğme ve ayar adları**: Uygulamanın her etiket için kendi çevirisi vardır. Sayfanın okurun ekranda gördüğüyle eşleşmesi için onu kalın olarak kullanın: etiketi `frontend/src/i18n/locales/<code>.js` içinde arayın. Uygulama o dile henüz çevrilmediyse İngilizce etiketi koruyun.
- **Vurgu kutuları** (`::: tip Başlık`): Türünü (`info`, `tip`, `warning`, `danger`) koruyun ve başlığı çevirin. Başlıksız bir vurgu kutusu, dil dosyasındaki `containers` sözcüğüyle etiketlenir.
- **Üslup**: O dilin okuruna göre yazın — sayfalar rehberdir, kelimesi kelimesine aktarım değil.

### Çevirileri güncel tutma

Bir İngilizce sayfa değiştiğinde, çevirilerinin aynı pull request’te değişmesi gerekmez: çevrilmiş bir sayfa çalışmaya devam eder ve `npm run i18n -- status <code>`, çevrildikten sonra İngilizce kaynağı değişen sayfaları listeler. Onları güncellemek iyi bir ilk katkıdır.

Testler (`docs/` içinde `npm test`) her dilin her sayfaya ve her site metnine sahip olduğunu ve çevrilmiş bir sayfanın İngilizce sayfanın başlıklarına, kod bloklarına, tablolarına, vurgu kutularına ve bağlantılarına hâlâ sahip olduğunu denetler.
