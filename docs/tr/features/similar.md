---
icon: lucide/sparkles
---

# Benzerler

**Benzerler**, verdiğiniz bir parçaya benzer parçaları YouTube Music’in kendi radyo karışımından bulur — YouTube’un parçanızdan sonra çaldıklarından. API anahtarı yok, kurulum yok.

## Nasıl kullanılır

Kenar çubuğundan **Benzerler**’i açın (**Müzik listeleri**’nin altında; telefonda **Daha fazla** sayfasında). **Sanatçı** veya **Parça** yazın (biri yeterli — yalnızca sanatçı yazarsanız en büyük hit’inden yola çıkılır), ardından **Benzerleri bul**’a tıklayın:

Yazmanız da gerekmez: uygulamadaki her parça satırında bir **Benzerler** düğmesi bulunur (indirme düğmesinin yanındaki değnek simgesi; Arama, Müzik listeleri ve Keşfet’te onun gibi dolu — En çok dinlenen şarkılar ve yapıştırılan bağlantılarda sade bir simge, Kitaplık, Albüm, Sanatçı ve Çalma listesi parçalarında ise bağlam menüsü öğesi). Bu sayfayı o parçayı zaten arayarak açar. Arama sonuçları da hiçbir şey indirmeden doğrudan satırdan tam olarak çalınır.

- **Tam olarak çal** — kapağa dokunun; parça indirilmiş olsun olmasın bu sunucudan doğrudan yerleşik oynatıcıya akıtılır.
- **İndir** — her satır videosunu zaten taşır ve hemen indirir: Downtify eşleşmeyi, diğer tüm indirmelerin kullandığı aynı [eşleştirme hattı](../how-it-works.md) üzerinden kuyruğa alır. Bundan sonra satır o indirmenin ilerlemesini, şarkı kitaplığınıza girince de bir onay işareti gösterir.
- **Sonsuz liste** — sona kadar kaydırmak, son parçanın kendi karışımından bir sonraki sayfayı yükler; son satırı geçen çalma da kuyruğu aynı şekilde, sonsuza dek büyütmeye devam eder.

## API

API başvurusunda [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) bölümüne bakın.
