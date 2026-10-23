---
title: Deemix
icon: lucide/music
---

# Deemix ses kaynağı

Deemix isteğe bağlı bir ses kaynağıdır ve varsayılan olarak kapalıdır. **Ayarlar → Ses kaynakları**
içinde slskd’nin altında yapılandırın ve kaynak sırasında etkinleştirin.
Kendi uyumlu Deemix sunucunuzu ve istenen kaliteye hakkı olan bir Deezer hesabını
gerektirir. Abonelik sağlamaz ya da bir aboneliği aşmaz.

## Kimlik bilgileri ve paylaşılan klasörler

Deemix’in normal oturum başına giriş modunu koruyun. Korumasız bir sunucuda tek
kullanıcı modunu etkinleştirmeyin: bağlantı uç noktası paylaşılan ARL’yi döndürür.

Deezer ARL’nizi içeren özel bir dosyayı Downtify’a bağlayın; yalnızca
hizmet hesabı okuyabilsin ve `DOWNTIFY_DEEMIX_ARL_FILE` değerini bu yola ayarlayın.
ARL yalnızca bir çerez oturumu açılırken okunur. Ayarlarda hiç saklanmaz, tarayıcıya
döndürülmez, günlüğe yazılmaz. Parola gibi davranın; onu sorunlarda ya da sohbette değil,
özel olarak edinin ve değiştirin. Entegrasyon Deemix’in sunucu genelindeki giriş veya
indirme ayarlarını asla değiştirmez.
Bağlantı testi indirme kuyruğa almaz.

| Ayar                          | Amaç                                                               |
| ----------------------------- | ------------------------------------------------------------------ |
| Sunucu URL’si                 | Deemix’in iç adresi, ör. `http://deemix:6595`                      |
| Deemix içindeki indirme klasörü | Genellikle `/downloads`                                          |
| Downtify içindeki aynı klasör | Paylaşılan bind mount, ör. `/deemix`; salt okunur desteklenir      |
| Kalite                        | MP3 128, MP3 320 veya FLAC; desteklenmeyen haklar açıkça başarısız olur |

Paylaşılan klasör, kaydedildiğinde harici kitaplık klasörü olarak kaydedilir.
Dosyalar Deemix’in sanatçı/albüm düzeninde orada kalır. Downtify biçimlerini,
etiketlerini, kapak resimlerini ve `.lrc` yan dosyalarını yeniden yazmadan korur.
Gömülü sözler ve aynı adlı `.lrc` dosyaları oynatıcı tarafından okunur.
Bu entegrasyon hiçbir ses ya da sözü silmez, taşımaz veya üretmez.

Bir Deezer parça bağlantısı o kaydı seçer. Kataloglar arası indirmeler, belirtildiğinde
albüm ve süre de eşleşen, açık ve kesin bir sanatçı/başlık eşleşmesi gerektirir.
Belirsiz bir eşleşme bir sonraki etkin kaynağa düşer.
Deemix kuyruğunun tamamlanmasının ardından dosya ve süre/kalite denetimi yapılır.
Entegrasyon elle oluşturulmuş Deemix işlerini asla temizlemez, iptal etmez veya değiştirmez.
Açık YouTube bağlantıları mevcut doğrudan indirme davranışını korur.

Bu kaynak kitaplıktaki mevcut bir parçayı otomatik olarak değiştirmez veya silmez.
Kitaplık yinelenen kayıt temizliği ve elle ses değiştirme ayrı kalır.
