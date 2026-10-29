---
icon: lucide/users
---

# Kullanıcılar ve oturum açma

Downtify’ı kullanan herkes bir **kullanıcı adı ve parolayla** oturum açar ve her kişinin kendi hesabı olabilir. Bir yönetici hesapları **Ayarlar → Kullanıcılar**’da yönetir ve herkesin ne yaptığını **Ayarlar → Etkinlik**’te görür.

## İlk kez oturum açma

Yeni bir sunucunun bir hesabı vardır:

| Kullanıcı adı | Parola |
|----------|----------|
| `admin` | `downtify` |

Onunla oturum açın ve **Ayarlar → Genel → Hesap** içinde **parolayı değiştirin**: Downtify’ı bilen herkes varsayılan parolayı bilir. Değiştirene kadar Downtify oturum açtıktan sonra size hatırlatır ve Ayarlar’da bir uyarı gösterir.

::: warning Sunucuyu dışarı açmadan önce varsayılan parolayı değiştirin
Varsayılan parola hiçbir şeyi korumaz. Downtify’ı ev ağınızın dışından erişilebilir yapmadan önce değiştirin — ve orada HTTPS kullanın (bkz. [Ters proxy arkasında](mobile-apps.md#behind-a-reverse-proxy)).
:::

### Eski bir sürümden yükseltme

Hesapsız bir sürüm çalıştıran bir sunucu aynı `admin` hesabını alır ve oturum açma sayfası bunu — bir yönetici oturum açana kadar — kullanılacak kullanıcı adı ve parolayla birlikte bir kez söyler:

- Eski **Oturum açmayı zorunlu kıl** seçeneği altında bir parola belirlemiştiyseniz, o parola `admin` için geçerli kalır.
- Aksi halde `downtify`’dır.

Yükseltmeden önce oturum açmış tarayıcılar yeniden oturum açar. Öncesinde eşleştirilmiş telefonlar eşleşmiş kalır ve artık `admin`’e aittir.

## Yöneticiler ve kullanıcılar

| | Yönetici | Kullanıcı |
|---|---|---|
| Dinleme, arama, indirme, beğenme, Keşfet, Müzik listeleri, Finder, podcastler | ✓ | ✓ |
| Telefon uygulamalarını eşleştirme (kendi hesabına) | ✓ | ✓ |
| Ayarlar → Genel (kendi hesabı ve tercihleri), Uygulamalar, Hakkında | ✓ | ✓ |
| Diğer tüm ayarlar (kaynaklar, dosyalar, etiketler, Navidrome, kitaplık, sunucu), sunucuyu yeniden adlandırma | ✓ | |
| [Kendi çalma listelerini paylaşma](#sharing-playlists) (salt görüntüleme), herkese açık olanları takip etme, kopya kaydetme | ✓ | ✓ (yönetici izin verdiğinde) |
| Dosya ve çalma listesi silme (bir kullanıcı yalnızca [indirdiklerini](#deleting-songs) ve kendi çalma listelerini), kendi çalma listesi izlemelerini ve podcast aboneliklerini yönetme, bir parçanın sesini değiştirme, sanatçı fotoğraflarını düzenleme | ✓ | ✓ (yalnızca kendininkiler) |
| [Şarkıları, albümleri ve sanatçıları kullanıcılardan gizleme](#hiding-from-users) | ✓ | |
| Kullanıcıları yönetme, etkinlik günlüğünü görme | ✓ | |

Yönetici gerektiren bir şey deneyen bir kullanıcı bunu söyleyen bir ileti alır.

## Kitaplığınız

Kitaplık paylaşımlıdır: her hesap, herkesin indirdiği her şarkıyı görür — Kitaplıkta, indirilmiş olarak işaretli arama sonuçlarında ve eşleştirilmiş bir telefonda. Dosyalar asla iki kez saklanmaz: iki kişi aynı şarkıyı indirdiğinde diskte bir kez durur, her birine bir sahiplikle.

Beğeniler, çalma listeleri (indirilen ve Kitaplıkta oluşturulan) ve indirme kuyruğu, yönetici olmadığınız sürece — ya da başkalarının görmesi için [bir çalma listesi paylaşmadığınız](#sharing-playlists) sürece — sizin kalır. Dinleme paylaşımlıdır — herkes herhangi bir parçayı çalabilir, önizleyebilir veya akıtabilir ve her şeyi kendi çalma listelerine ekleyebilir. Başkasının zaten indirdiği bir parçayı istemek, onu iki kez getirmek yerine onun işine katılır: tek kuyruk satırı, tek indirme ve her birine bir sahiplik — bekleyen herkes kuyruktaki yerini görür.

Podcastler, çalma listesi izlemeleri ve Keşfet geçmişi de aynı şekilde çalışır: her hesap kendi programlarına abone olur, kendi çalma listelerini ve sanatçılarını takip eder ve kendi önerilerini eğitir. Bir yönetici her hesabın satırlarını görür. Dinlemenin kendisi paylaşımlı kalır — herkes herhangi bir parçayı çalabilir, önizleyebilir veya akıtabilir.

### Çalma listelerini paylaşma

Bir çalma listesi, sahibi onu paylaşana kadar — çalma listesi sayfasındaki **Paylaş…** veya **⋯** menüsünden — sahibine (ve yöneticilere) özeldir. Oynatma hesaplar arasında zaten paylaşımlıdır; bu yalnızca bir listeyi kimin *görebileceğiyle* ilgilidir. *Beğenilen şarkılar* dışındaki her çalma listesi paylaşılabilir, içe aktarılanlar dahil.

| Görünürlük | Kim görür |
|------------|-------------|
| **Özel** | Yalnızca sahibi ve yöneticiler — varsayılan |
| **Belirli kişiler** | Sahibinin seçtiği kullanıcı adları |
| **Herkese açık** | Sunucudaki herkes |

Başkalarının çalma listeleri asla sizinkilerle karışmaz. Kitaplığın **Çalma listeleri** sekmesi onları sizinkilerin altında iki bölümde listeler; her giriş sahibiyle etiketlenir:

- **Benimle paylaşılanlar** — size adınızla yönelik çalma listeleri, her zaman gösterilir. Yeni paylaşılan, siz açana kadar bir **Yeni** işareti taşır.
- **Herkese açık listeler** — herkesin herkese açık olanları, sahibine ve ada göre sıralı, sekmenin süzgeciyle aranabilir, sahibini, şarkı sayısını ve takip edip etmediğinizi gösterir. Bölüm kapalı başlar ve **Ayarlar › Genel › Herkese açık listeleri göster** ile tamamen gizleyebilirsiniz (varsayılan olarak açık; temanız gibi sizin).

Kenar çubuğu ayrıca sizinle paylaşılanlardan ve takip ettiğiniz herkese açık çalma listelerinden birkaçını gösterir.

**Görüntüleyenin yapabilecekleri:** oynatma, karıştırma, kuyruğa ekleme, ZIP olarak indirme (veya bir telefon ya da masaüstü uygulamasına), listelerinde kalması için herkese açık bir çalma listesini **Takip et** — *Herkese açık listeleri göster* kapalıyken bile — ve sahibinin değişikliklerini izleme, ve **Kopyasını kaydet**: görebildiği şarkılarla kendine ait özel, düzenlenebilir bir çalma listesi. Görüntüleyen, başkasının çalma listesini düzenleyemez, yeniden adlandıramaz, silemez, paylaşamaz veya ayıramaz. Kitaplıkta oluşturulan bir listenin sahibi, paylaştığı kişilerden bazılarını düzenleyici yapabilir; onlar şarkı da ekleyip çıkarabilir — bkz. [Birlikte düzenlenen listeler](collaborative-playlists.md).

**Paylaşımı kaldırma:** sahibi bir çalma listesini yeniden özel yaparsa ya da birini listeden çıkarırsa, o kişinin listelerinden hemen çıkar (takip edilmiş olsun olmasın); herkese açık olmaktan çıkan bir çalma listesi artık takip edilmez. İnsanların zaten kaydettiği kopyalar onlarda kalır. Paylaşılan bir çalma listesini yeniden adlandırmak paylaşımlı tutar; silmek paylaşımı da götürür. Bir yöneticinin [kullanıcılardan gizlediği](#hiding-from-users) şarkılar, her yerde olduğu gibi onlar için paylaşılan bir çalma listesinin parçalarından hariç tutulur.

Bir yönetici bunun tamamını **Ayarlar › Kitaplık › Kullanıcıların liste paylaşmasına izin ver** ile kapatabilir (varsayılan olarak açık). Kapalıyken her paylaşım gizlenir ve kimse paylaşamaz ya da takip edemez — yeniden açıldığında paylaşımlar geri gelir.

Eşleştirilmiş uygulamalar aynı listeleri alır: [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) her birinin sahibini ve salt görüntüleme olup olmadığını söyler, WebSocket’teki `playlists_changed` onlara yenilemelerini bildirir.

### Kullanıcılardan gizleme

Yöneticiler diğer hesapların ne gördüğüne karar verir. Bir yönetici bir şey gizleyene kadar her şey herkese görünürdür: bir **şarkı**, bütün bir **albüm** ya da bütün bir **sanatçı**. Gizlenen öğeler Kitaplıktan, aramanın “kitaplıkta” işaretlerinden, çalma listelerinin parça listelerinden ve eşleştirilmiş bir telefonun eşitlediklerinden çıkar — kullanıcılar için, yöneticiler için değil.

- **Kitaplıkta** bir şarkının, albümün veya sanatçının `…` menüsünü açın ve **Kullanıcılardan gizle**’yi seçin (geri almak için **Kullanıcılara göster**). Parçalar sekmesinde birkaç şarkı seçin ve seçim çubuğundaki **Kullanıcılardan gizle**’yi kullanın.
- Yöneticiler her şeyi görmeye devam eder. Gizlenen, küçük çizili bir göz taşır ve ipucu nedenini söyler: tek başına gizlenmiş, albümüyle veya sanatçısıyla birlikte.
- **Ayarlar › Kullanıcılar › Kullanıcılardan gizlenenler** her gizli sanatçıyı, albümü ve şarkıyı, yanlarında **Kullanıcılara göster** ile listeler.
- Gizli bir şarkı başka bir klasöre taşındığında ve [Kitaplığı iyileştir](library-upgrade.md) ya da [Sesi değiştir](replace-audio.md) dosyasını yeniden yazdığında gizli kalır. Dosyayı silmek kuralı unutturur.
- Bir albüm kuralı albümün sanatçısı ve başlığıyla, bir sanatçı kuralı ise Kitaplığın şarkıyı altında gruplandırdığı sanatçıyla eşleşir — Kitaplığın Albümler ve Sanatçılar sekmelerinin kullandığı aynı adlar.

::: info Gizleme, neyin listelendiğiyle ilgilidir
Hesapların uygulamada ne gördüğünü denetler, adresini zaten bildikleri bir dosyayı kimin getirebileceğini değil. Hassas dosyaları korumak için kullanmayın.
:::

Gizleme ve gösterme [etkinlik günlüğüne](#activity) kaydedilir.

### Şarkıları silme

Bir şarkıyı silmek onu herkes için diskten kaldırır, bu yüzden onu indirene bağlıdır. Bir yönetici her şeyi silebilir. Bir kullanıcı kendi indirdiği bir şarkıyı silebilir; başkası da aynı şarkıyı indirdiyse silmek yalnızca kendi hak iddiasından vazgeçer ve şarkı paylaşılan kitaplıkta kalır. Bir hesap üzerinden kimsenin indirmediği bir şarkıyı (bir çalma listesi izleyici taraması, hesaplardan önceki bir indirme, bir [ek klasör](external-library.md)) yalnızca bir yönetici silebilir. Kendi çalma listenizi silmek başkasının dosyalarını asla beraberinde götürmez.

### Hesap başına kullanım

**Ayarlar › Kullanıcılar**, her hesabın altında neleri tuttuğunu listeler: parçalar ve boyutları, beğeniler, çalma listeleri, istenen indirmeler ve iki yöndeki trafik (kaynaktan getirilen ve istemcilere sunulan), altında herkesin toplamlarıyla. “Parçalar”, bir hesabın indirdiği şarkıları sayar, görebildiklerini değil.

## Hesabınız ve tercihleriniz

**Ayarlar → Genel**, **Hesap**’ınızla başlar: kullanıcı adınızı veya parolanızı değiştirin ya da oturumu kapatın. Kenar çubuğundan da (telefonda **Daha fazla**) çıkış yapabilirsiniz.

**Genel**’in geri kalanı — tema, dil, oynatıcıda sözleri gösterme, arama sonuçlarında albümler — **sizindir**: oturum açtığınız her tarayıcıda hesabınızı izler ve başkası için hiçbir şeyi değiştirmez.

**Ayarlar → Uygulamalar**, hesabınıza eşleştirilmiş telefonları listeler (yönetici herkesinkini, sahipleriyle birlikte görür). **Her yerden çıkış yap**, uygulamalarınızın eşleştirmesini kaldırır ve sizi her tarayıcıdan çıkarır.

## Kullanıcıları yönetme

**Ayarlar → Kullanıcılar** içinde bir yönetici şunları yapabilir:

- **Kullanıcı ekle** — kullanıcı adı (3 ila 32 harf, rakam, `.`, `-` veya `_`), parola (en az 8 karakter) ve rol.
- Bir kullanıcıyı **düzenle** — yeniden adlandır, yönetici ya da kullanıcı yap veya yeni bir parola ver (bu, onu tarayıcılarından çıkarır; uygulamaları eşleşmiş kalır).
- Bir kullanıcıyı **sil** — uygulamalarının eşleştirmesi kaldırılır, tarayıcıları çıkarılır. Dosyaları diskte kalır (yöneticiler yine görebilir); beğenileri, çalma listeleri, podcast abonelikleri, izlemeleri, öneri geçmişi ve trafik sayaçları onunla gider.
- **Herkesin oturumunu kapat** — her kullanıcının her uygulamasının eşleştirmesi kaldırılır ve her tarayıcı çıkarılır, sizinki de.

Her zaman en az bir yönetici vardır: sonuncusu silinemez ya da kullanıcı yapılamaz ve kendi hesabınızı silemezsiniz.

## Etkinlik

**Ayarlar → Etkinlik** (yöneticiler), Jellyfin’in panosu gibi şunları gösterir:

- **Şimdi çalıyor** — her tarayıcı ve uygulamanın ne çaldığı, kim tarafından, şarkının neresinde olduğu ve duraklatılıp duraklatılmadığı. Birkaç saniyede bir yenilenir.
- **Geçmiş** — oturum açmalar (ve başarısızlar, geldikleri adresle), çıkışlar, çalınan şarkılar, indirmeler, beğeniler, silinen dosyalar, kullanıcılardan gizlenen ya da onlara gösterilen şarkılar, eşleştirilen ve eşleştirmesi kaldırılan uygulamalar, eklenen, değiştirilen ya da silinen hesaplar, değiştirilen parolalar ve ayarlar. Kullanıcıya veya türe göre süzün. Kaydedilen ayarlar yalnızca adıyla listelenir, asla değerleriyle. Girdiler 90 gün saklanır.

Uygulamalar da çaldıklarını bildirir — bkz. [mobil istemci sözleşmesi](../mobile-client-contract.md#8-report-plays).

## Hesapları kapatma

Yalnızca sizin erişebildiğiniz bir sunucu — kendi bilgisayarınızda ya da zaten parola isteyen bir şeyin arkasında — hesaplara hiç ihtiyaç duymayabilir. `DOWNTIFY_DISABLE_AUTH=true` ayarlayın (bkz. [Ortam değişkenleri](../getting-started/environment-variables.md#mobile-apps-and-sign-in)):

```yaml
environment:
  - DOWNTIFY_DISABLE_AUTH=true
```

Sonra:

- Oturum açma sayfası yoktur: Downtify’ı açan kim olursa ilk yönetici olarak kullanır (yeni sunucuda `admin`).
- Çıkış düğmeleri, **Ayarlar → Kullanıcılar**, **Ayarlar → Genel**’in **Hesap** kısmı ve **Ayarlar → Uygulamalar**’daki **Her yerden çıkış yap** kaybolur.
- Telefonlar yine eşleştirilebilir (o yöneticiye) ve **Ayarlar → Etkinlik** neyin nerede çaldığını göstermeye devam eder.
- Tema, dil ve diğer **Genel** tercihleri o yöneticinin olarak tutulur.

::: warning Sunucuya erişebilen herkes her şeyi yapabilir
Hesaplar kapalıyken hiçbir şey kim olduğunuzu sormaz: ağınızdaki — port açıksa internetteki — herkes ayarları değiştirebilir, müzik silebilir ve telefon eşleştirebilir. Başkalarının erişebildiği bir sunucuda hesapları kapatmayın.
:::

`false` yapın (ya da kaldırın), oturum açma yeniden zorunlu olur; hesaplar, parolalar ve uygulamalar eskisi gibi durur.

## Parolayı mı unuttunuz?

Bunu sunucuda çalıştırın — `admin` `downtify` parolasını geri alır (yeniden adlandırılmış ya da silinmişse yönetici olarak yeniden oluşturulur); diğer hesaplara ve eşleştirilmiş uygulamalara dokunulmaz:

```bash
docker exec downtify python main.py auth-reset
```

Docker dışında, Downtify’ın klasöründe `python main.py auth-reset` (veya `uv run python main.py auth-reset`) çalıştırın. Sonra oturum açıp parolayı değiştirin.

## Betikler ve API

Her API çağrısı artık kimlik bilgisi gerektirir (bkz. [API başvurusu](../api-reference.md#server-and-sign-in)). Bir betik `POST /api/auth/login` ile oturum açıp `downtify_session` çerezini tutabilir ya da eşleştirilmiş bir cihazın belirtecini kullanabilir.
