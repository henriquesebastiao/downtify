---
icon: lucide/trending-up
---

# Müzik listeleri

**Müzik listeleri**, Deezer’ın kendi küresel listesini gösterir — tür filtresi yok, şu anda dünya genelinde neyin gündemde olduğu — Deezer hesabı ya da API anahtarı gerekmeden.

## Nasıl kullanılır

Kenar çubuğundan (telefonda **Daha fazla** sayfasından) **Müzik listeleri**’ni açın. Dört sekme aynı listeyi okur: **Parçalar**, **Albümler**, **Sanatçılar** ve **Çalma listeleri**.

- **Parçalar** — sıralı bir liste. İndirmeden önce YouTube’dan tam olarak, doğrudan yerleşik oynatıcıda dinlemek için birine basın (ya da satırına dokunun). Bir satırı indirmek, bir arama sonucuyla aynı şekilde çalışır: Downtify parçanın başlığı, sanatçısı ve süresi için YouTube Music’te (olmazsa standart YouTube’da) en yakın eşleşmeyi arar; diğer tüm indirmelerin kullandığı aynı [eşleştirme hattını](../how-it-works.md) kullanır. Bir parça indirildikten sonra satırı onu akıtmak yerine kitaplığınızdan çalar.
- **Albümler**, **Sanatçılar** ve **Çalma listeleri** — kapak ızgaraları. Birine tıklamak onu çözümler ([`GET /api/url/resolve`](../api-reference.md#get-apiurlresolve)); sanki o Deezer bağlantısını arama kutusuna kendiniz yapıştırmışsınız gibi: parça listesi yüklenir, seçmeye ve indirmeye hazır.

## Parçalar neden doğrudan buradan indirilir (ve tam çalınır), ama albümler, sanatçılar ve çalma listeleri önce bir sayfa açar

Bir liste parçasının indirilmek için çözümleme adımına ihtiyacı yoktur: Deezer başlığı, sanatçıyı ve albüm adını zaten verir; bu, serbest metin arama sonucunda olduğu gibi YouTube’da arayıp eşleştirmeye yeter. Bir albüm, sanatçı ya da çalma listesinin ise bu adıma ihtiyacı vardır — bağlantısını parça listesine dönüştürmek —, bu yüzden kartı doğrudan ızgaradan indirmek yerine çözümlenmiş sayfayı açar. Bir parça satırını çalmak YouTube’dan tam olarak akıtır (albümler, sanatçılar ya da çalma listeleri için asla) — her parça satırının kullandığı aynı akış, yalnızca listenin başlığı ve sanatçısıyla beslenir.

## API

API başvurusunda [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart) bölümüne bakın.
