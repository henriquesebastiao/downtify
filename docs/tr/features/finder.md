---
icon: lucide/columns-3
---

# Finder

**Finder**, indirmeden önce Deezer kataloğunu keşfetmenin bir yoludur. Deezer’da arama yaparsınız, bir sanatçı açarsınız ve onu macOS Finder’ın sütun görünümü gibi yan yana üç sütunda gezersiniz: sanatçı, diskografisi ve bir albümün parçaları. Deezer hesabı ya da API anahtarı gerekmez.

## Arama

Kenar çubuğundan **Keşfet**’i açın (telefonda: **Daha fazla → Keşfet**): Finder’ın arama kutusu sayfanın üstündedir, yanında son Finder aramalarınız vardır. Arama, Keşfet’in önerilerinin yerine bulunanları koyar — **Tümü / Şarkılar / Albümler / Sanatçılar** çipleriyle şarkılar, albümler ve sanatçılar; normal Arama sayfasındaki gibi ama yalnızca Deezer’dan. Önerileri yeniden görmek için kutuyu temizleyin (**×**) veya geri gidin; son bir arama tek tıkla yeniden çalışır, **Temizle** hepsini unutturur. Son aramalar yalnızca bu tarayıcıda tutulur.

Keşfet’in önerdiği bir sanatçının **⋯** menüsündeki **Şarkı bul**, o sanatçının şarkılarını burada bir arama olarak gösterir: Deezer’da sanatçının adı aranır ve yalnızca tam o sanatçıya ait şarkılar — Deezer kimliğiyle eşleştirilir, yani aynı adı taşıyan başka biri ya da yalnızca bu adı taşıyan bir şarkı dışarıda kalır — ilk birkaç yüze kadar listelenir.

- **Şarkılar** tam olarak akıtılır ve herhangi bir arama sonucu gibi indirilir. Downtify şarkıyı başlık, sanatçı ve süreye göre YouTube Music’te (olmazsa YouTube’da) eşleştirir. Bir şarkının başlığına tıklamak albümünü sütun görünümünde, şarkı vurgulanmış olarak açar.
- **Albümler** sanatçıları üzerinde, o albüm seçili olarak açılır. Kapaktaki indirme düğmesi albümün tamamını sıraya alır.
- **Sanatçılar** sütun görünümünü o sanatçıda açar.

## Sütun görünümü

| Sütun | Ne gösterir |
| --- | --- |
| **Sanatçı** | Sanatçının fotoğrafı ve albüm sayısı, arayüzün dilindeki biyografisi (genişletilebilir), en popüler 10 parçası ve “Hayranlar bunları da seviyor” (ilgili sanatçılar). |
| **Diskografi** | Her albüm, single, EP ve derleme; en yeniden eskiye, kapağı, başlığı, yayın türü, yılı ve parça sayısıyla. Çipler yayın türüne göre süzer. |
| **Parçalar** | Seçili albümün kapağı ve başlığı, sanatçısı, yılı, parça sayısı ve süresi. Bir bilgi paneli yayın tarihini, plak şirketini, türleri, jenerik bilgilerini ve UPC’yi listeler. Altında albümün parçaları yer alır: her biri indirilene kadar tam olarak akıtılır, sonra kitaplığınızdan çalar; hepsini sıraya almak için **Albümü indir** düğmesi vardır. |

Popüler bir parçaya tıklamak albümünü seçer ve parçayı vurgular; iki sütun da görünür olana kadar yumuşakça kayar (sistem hareketi azaltacak şekilde ayarlıysa anında) ve albümün parçaları ekrana geldiğinde parça tam olarak çalmaya başlar — akıtılarak veya kitaplığınızdaysa şarkının kendisi. Çalarken yeniden tıklamak onu duraklatmaz; sayfayı bir parçayı gösteren bağlantıdan açmak hiçbir şey başlatmaz. İlgili bir sanatçıya tıklamak o sanatçıyı açar, tarayıcının geri düğmesi bir öncekine döner. Sütunların üstündeki yol çubuğu (**Keşfet › sanatçı › albüm**) aramaya (sütunlar bir aramadan açılmadıysa Keşfet’e) veya yalnızca sanatçıya geri götürür. Açık olan URL’de saklanır; yani yeniden yüklemeden etkilenmez ve yer imi yapılabilir.

Geniş ekranda, bir sütunu genişletmek ya da daraltmak için iki sütun arasındaki kenarı sürükleyin; ya da odaklanıp ok tuşlarını kullanın. Çift tıklama varsayılan genişlikleri geri getirir. Sanatçı ve diskografi sütunlarının üstündeki ok düğmesi sütunu yalnızca resimlerine daraltır: sanatçının fotoğrafı, popüler parçalarının kapakları ve ilgili sanatçıların fotoğrafları ya da albüm kapakları. Her resim hâlâ tam satırı gibi çalışır ve adı üzerine gelince görünür. Genişlikler ve daraltılmış sütunlar yalnızca sayfada olduğunuz sürece kalır: hiçbir zaman kaydedilmez, yeniden yükleme ya da Finder’dan çıkmak onları sıfırlar.

Telefonda sütunlar yan yana durur ve aralarında kaydırırsınız. Bir albüm seçmek parçalarına kaydırır.

::: info Parça sayıları neden biraz sonra görünür
Deezer’ın diskografi listesinde parça sayısı yoktur; bu yüzden Downtify her albümün sayısını ayrı ayrı, bir seferde birkaç albüm olacak şekilde ve Deezer’ın 5 saniyede 50 istek sınırının altında kalarak ister. Sayılar siz bakarken görünür ve Downtify yeniden başlatılana kadar hatırlanır. Sayısı alınamayan bir albümde `…` görünür.
:::

## API

API Başvurusu’nda [`GET /api/finder/search`](../api-reference.md#get-apifindersearch) ve sonrasındaki uç noktalara bakın.
