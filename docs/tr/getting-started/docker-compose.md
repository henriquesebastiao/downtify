---
icon: lucide/file-code
---

# Docker Compose

Docker Compose, kalıcı ev sunucusu kurulumlarında Downtify’ı çalıştırmanın önerilen yoludur. Güncellemeleri, yedeklemeleri ve yapılandırma değişikliklerini kolaylaştırır.

## Asgari kurulum

Bir `docker-compose.yml` dosyası oluşturun:

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped

volumes:
  downtify_data:
```

Başlatın:

```bash
docker compose up -d
```

**[http://localhost:8000](http://localhost:8000)** adresini açın.

## slskd (Soulseek) ile

[slskd’yi ses kaynağı olarak](../features/slskd-navidrome.md) kullanmak için slskd’nin indirme klasörünü de Downtify’a bağlayın — slskd kapsayıcınızın yazdığı **aynı ana makine klasörünü**:

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

Ardından **Ayarlar → Ses kaynakları → slskd** içinde slskd’yi etkinleştirin, URL’sini (iki kapsayıcı bir Docker ağını paylaşıyorsa örneğin `http://slskd:5030`) ve API anahtarını girin, indirme klasörünü `/slskd` olarak ayarlayın.

## Mevcut müzik klasörleri

Kitaplığın ana makinede zaten tuttuğunuz bir koleksiyonu görmesi için onu aynı şekilde [bağlayın](../features/external-library.md) ve **Ayarlar → Kitaplık** içine **kapsayıcıdaki** yolu yazın:

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## Sunucuyu uygulamalardan bulma

[Mobil uygulamalar](../features/mobile-apps.md#finding-the-server-on-your-network) ağınızdaki Downtify sunucularını mDNS ile listeler. Docker’ın varsayılan köprü ağında bu duyuru Docker’dan asla çıkmaz, bu yüzden telefonlar onu görmez. Listelenmesi için kapsayıcıyı ana makinenin ağında çalıştırın — `ports:` eşlemesi o zaman geçerli olmaz ve Downtify doğrudan `DOWNTIFY_PORT` üzerinde dinler:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    network_mode: host
    environment:
      - DOWNTIFY_PORT=8000
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

Aksi halde sunucunun adresini uygulamaya yazmanız yeter (`http://<ana makine IP’si>:8000`); başka hiçbir şey keşfe bağlı değildir.

## Özel bağlantı noktası

8000 numaralı bağlantı noktası zaten kullanımdaysa farklı bir ana makine bağlantı noktası eşleyin ve kapsayıcının iç tarafta aynı bağlantı noktasını dinlemesi için `DOWNTIFY_PORT` ortam değişkenini ayarlayın:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '9090:30321'
    environment:
      - DOWNTIFY_PORT=30321
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

Bağlantı noktasını `DOWNTIFY_PORT` ayarlamak yerine **Ayarlar → Sunucu → Port** içinden de seçebilirsiniz (ayarlandığında Ayarlar’a üstündür). Varsayılan köprü ağında `ports:` eşlemesini aynı bağlantı noktasına çevirin ve kapsayıcıyı yeniden oluşturun — [Bağlantı noktasını değiştirme](../features/server.md#changing-the-port) bölümüne bakın.

## Özel DNS ile (önerilir)

Bazı internet sağlayıcıları ve kurumsal ağlar YouTube’u engeller. Açık DNS çözücüleri eklemek güvenilirliği artırır:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    dns:
      - 1.1.1.1
      - 1.0.0.1
    restart: unless-stopped
```

## Güncelleme

```bash
docker compose pull
docker compose up -d
```

Müziğiniz ve ayarlarınız birimlerde korunur.

## Birimler

| Compose dosyasındaki yol | Amaç |
|------------------------------|---------|
| `./downloads:/downloads` | İndirilen ses dosyaları (yerel dizin) |
| `downtify_data:/data` | Uygulama veritabanı ve ayarları (adlandırılmış birim) |

Kendiniz yönetmeyi tercih ederseniz adlandırılmış birimi yerel bir yolla (`./data:/data`) değiştirebilirsiniz.
