---
icon: lucide/hard-drive
---

# Sunucu ayarları

**Ayarlar → Sunucu**, sunucunun kendisinin nasıl çalıştığını belirler. Yalnızca yöneticiler görür ([Kullanıcılar ve oturum açma](users.md#admins-and-users) sayfasına bakın).

## Bağlantı noktasını değiştirme

Downtify **8000** numaralı bağlantı noktasını dinler. Bir yönetici **Ayarlar → Sunucu → Port** içinden başka birini seçebilir (1024–65535):

- **Kaydet**, sunucu bir sonraki başlayışında kullanılmak üzere saklar.
- **Kaydet ve yeniden başlat**, sunucuyu hemen bu portla yeniden başlatır. Süren indirmeler durur, sayfalar ve uygulamalar yeniden bağlanır. Sunucunun kendi adresinde (ör. `http://nas:8000`) açılmış bir sayfa sunucuyu bekler ve yeni adresi kendiliğinden açar; oturumunuz açık kalır.

Port, `DOWNTIFY_PORT` (veya `PORT`) ortam değişkeninden ya da komut satırındaki `--port` seçeneğinden geliyorsa — bunlar her zaman önceliklidir — alan kullanılan portu gösterir ama düzenlenemez, sayfa da hangisinin belirlediğini söyler. Portu Ayarlar’dan seçmek için onu kaldırın (ve yeniden başlatın).

::: warning Docker’ın bridge ağı sabit bir portu eşler
Varsayılan Docker kurulumunda (`ports: - '8000:8000'`) kapsayıcının portu eşlemeyle uyuşmalıdır. Ayarlar’da değiştirdikten sonra eşlemeyi yeni porta çevirin (`'9000:9000'`) ve kapsayıcıyı yeniden oluşturun — ya da `network_mode: host` ile çalıştırın. Aksi halde Downtify’a ulaşılamaz. Geri girmek için `DOWNTIFY_PORT` değerini eski porta ayarlayın: Ayarlar’dan önceliklidir.
:::

Bir [ters proxy](mobile-apps.md#behind-a-reverse-proxy) arkasındaysanız proxy’yi de yeni porta yönlendirin. [Eşleştirilmiş uygulamalar](mobile-apps.md) kendilerine verilen adresi kullanır: port değişikliğinden sonra yenisini uygulamaya girin.
