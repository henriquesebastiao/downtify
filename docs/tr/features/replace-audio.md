---
icon: lucide/replace
---

# Sesi değiştir

Downtify her şarkının sesini otomatik seçer ve bazen yanlışını seçer: aynı adlı başka bir şarkı, canlı bir kayıt, bir remix veya uzun girişli bir yükleme. **Sesi değiştir** doğru sürümü elle seçmenizi sağlar. Parça her yerde yerini korur — çalma listelerinde, M3U dosyalarında, beğenilerde ve eşleştirilmiş uygulamalarda — ve yalnızca ses değişir.

Yalnızca yöneticiler sesi değiştirebilir ([Kullanıcılar ve oturum açma](users.md#admins-and-users) sayfasına bakın).

## Bir parçanın sesini değiştirme

1. **Kitaplık**’ta parçanın menüsünü açın (sağ tık ya da **⋯** düğmesi) ve **Sesi değiştir…**’i seçin.
2. Downtify “Sanatçı - Başlık” için **YouTube Music**’te ve **YouTube**’da arar ve bulduklarını listeler. Tam istediğiniz yüklemeyi bulmak için aramayı değiştirin ya da tek bir videoya veya şarkıya ait bir YouTube ya da YouTube Music bağlantısı yapıştırın.
3. Bir sürüm seçin. Her biri nereden geldiğini ve ne kadar sürdüğünü, dosyanızın süresinin yanında gösterir. Dosyanızın süresine 3 saniye içinde olan sürüm vurgulanır. ↗ düğmesi onu YouTube’da açar; böylece seçmeden önce dinleyebilirsiniz.
4. **Sesi değiştir**’e basın. Değiştirme bir indirme gibi çalışır: ilerlemesini iletişim kutusunda ve **Kuyruk**’ta gösterir, bittiğinde iletişim kutusu söyler.

Başarısız olursa (video kullanılamıyor ya da YouTube oturum açmanızı istiyor — [YouTube çerezleri](youtube-cookies.md)’ne bakın) dosyanız tam olarak olduğu gibi kalır. Kuyruktaki **Tekrar dene** aynı videoyu yeniden dener; oraya başka bir bağlantı yapıştırmak onunla değiştirir.

## Aynı kalanlar

- **Dosya.** Yeni ses aynı yola, aynı biçimde yazılır: bir `.mp3` MP3 olarak kalır ([İndirme ayarları](download-settings.md)’nda seçilen bit hızıyla), bir `.flac` FLAC olarak kalır ve böyle devam eder. Böylece dosyaya işaret eden her çalma listesi, M3U dosyası, beğenilen şarkı, Navidrome girişi ve eşleştirilmiş uygulama ona işaret etmeyi sürdürür.
- **Etiketler.** Başlık, sanatçılar, albüm, parça numarası, yıl, kapak resmi, gömülü sözler ve diğer tüm etiketler eski dosyadan yeni sese olduğu gibi kopyalanır. `.lrc` yan dosyasına dokunulmaz. Eşzamanlı sözler eski sese göre zamanlanmıştı: yeni sürüm farklı bir noktada başlıyorsa kayabilirler.
- **Tarih.** Dosya değiştirilme tarihini korur; bu yüzden “Son eklenenler”in en üstüne atlamaz.

Yalnızca `.mp3`, `.flac`, `.m4a`, `.ogg` ve `.opus` dosyaları — Downtify’ın yazdığı biçimler — değiştirilebilir.

## Nasıl çalışır

Seçilen video, dosyanın yanına kitaplığın yok saydığı geçici bir adla (`<ad>.downtify-upgrade.<uzantı>`) indirilir, dosyanın biçimine dönüştürülür, okunabilir ses olduğu denetlenir, eski dosyanın etiketleri verilir ve ancak ondan sonra eski dosyanın üzerine taşınır. API, [API başvurusu](../api-reference.md#get-apilibraryreplacecandidates)’ndadır.
