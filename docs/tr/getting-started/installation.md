---
icon: lucide/download
---

# Kurulum

Downtify’ı çalıştırmanın en hızlı yolu tek bir `docker run` komutudur. Ana makinede Python, Node.js veya başka sistem bağımlılığına gerek yok — her şey imajın içinde gelir.

## Ön koşullar

- [Docker](https://docs.docker.com/get-docker/) kurulu ve çalışıyor

## Docker run

```bash
docker run -d \
  --name downtify \
  -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

`/path/to/music` yerine müziğinizin kaydedilmesini istediğiniz dizini yazın.

Kapsayıcı başladığında tarayıcınızda **[http://localhost:8000](http://localhost:8000)** adresini açın.

## Birimler

| Birim | Amaç |
|--------|---------|
| `/downloads` | İndirilen ses dosyaları |
| `/data` | Uygulama veritabanı ve kalıcı ayarlar |

Her iki birim de kapsayıcı yeniden başlatmaları ve yükseltmeleri boyunca kalıcıdır. `/downloads` birimi, ana makinenizdeki herhangi bir dizin ya da adlandırılmış bir Docker birimi olabilir.

## Özel bağlantı noktası

Downtify’ı farklı bir ana makine bağlantı noktasında sunmak için `-p`’nin sol tarafını değiştirin:

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # ana makine:kapsayıcı
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Ardından **[http://localhost:9090](http://localhost:9090)** adresini açın.

## Güncelleme

En son imajı çekin ve kapsayıcıyı yeniden oluşturun:

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Müziğiniz ve ayarlarınız birimlerde korunur.

## Sırada ne var?

- **[Docker Compose](docker-compose.md)** — kapsayıcıyı uzun vadede yönetmenin daha kolay yolu
- **[Ortam değişkenleri](environment-variables.md)** — anti-bot davranışını ve diğer gelişmiş seçenekleri ayarlayın
- **[İndirme ayarları](../features/download-settings.md)** — biçiminizi ve bit hızınızı seçin
