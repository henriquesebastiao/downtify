---
icon: lucide/download
---

# Güncelleme bildirimleri

Downtify, kendi [GitHub Releases sayfasını](https://github.com/henriquesebastiao/downtify/releases) saatte bir kontrol eder. Daha yeni bir sürüm çıktığında her sayfada kenar çubuğunun altında bir bildirim görünür — telefonlarda **Daha fazla** sekmesinde bir nokta ve sayfasının en üstünde bir satır — ayrıca **Ayarlar → Hakkında** içinde:

> ✦ 3.0.1 güncellemesi mevcut

Bu sürümü GitHub’da açmak için üzerine tıklayın.

## Nasıl çalışır

- Arka uçtaki bir arka plan görevi (`downtify/update_check.py`) en son sürümü GitHub API’sinden başlangıçta hemen bir kez, ardından her saat alır. “Gönder ve unut” türündedir: arayüzdeki hiçbir şey onu beklemez.
- Web arayüzü önbelleğe alınmış sonucu saatte bir `GET /api/check_update` üzerinden okur ([API başvurusu](../api-reference.md)’na bakın) ve daha yeni bir sürüm bulunduğunda bildirimi gösterir.
- Sürümler sayısal olarak karşılaştırılır (`2.10.0` < `2.9.0` ifadesi, düz bir metin karşılaştırmasının aksine, yanlıştır) ve sürüm etiketindeki isteğe bağlı `v` öneki yok sayılır.

## GitHub’a ulaşılamazsa

Başarısız bir kontrol (çevrimdışı ana makine, GitHub istek sınırı) günlüğe yazılır ve bir sonraki saatlik turda yeniden denenir — varsa önceki sonuç o zamana kadar geçerli kalır. Kontrol, Downtify’ın yaptığı başka hiçbir şeyi engellemez; bunun için kullanıcıya gösterilen bir hata yoktur.

## Hiçbir şey otomatik indirilmez

Bu yalnızca yeni bir sürüm olduğunu *söyler* — Downtify kendini güncellemez. Gerçekten güncellemek için yeni imajı çekin ve kapsayıcıyı yeniden oluşturun:

```bash
docker compose pull
docker compose up -d
```
