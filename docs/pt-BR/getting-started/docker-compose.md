---
icon: lucide/file-code
---

# Docker Compose

O Docker Compose é a forma recomendada de rodar o Downtify em servidores domésticos permanentes. Ele facilita atualizações, backups e mudanças de configuração.

## Configuração mínima

Crie um arquivo `docker-compose.yml`:

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

Inicie-o:

```bash
docker compose up -d
```

Abra **[http://localhost:8000](http://localhost:8000)**.

## Com slskd (Soulseek)

Para usar o [slskd como fonte de áudio](../features/slskd-navidrome.md), monte também a pasta de downloads do slskd no Downtify — a **mesma pasta do host** em que o seu contêiner slskd grava:

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

Depois, em **Configurações → Fontes de áudio → slskd**, ative o slskd, informe a URL dele (por exemplo `http://slskd:5030` quando os dois contêineres compartilham uma rede Docker) e a chave de API, e defina a pasta de download como `/slskd`.

## Pastas de músicas existentes

Para que a Biblioteca reconheça uma coleção que você já mantém no host, [monte-a](../features/external-library.md) do mesmo jeito e digite o caminho **do contêiner** em **Configurações → Biblioteca**:

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## Encontrando o servidor pelos apps

Os [apps para celular](../features/mobile-apps.md#finding-the-server-on-your-network) listam os servidores Downtify da sua rede por mDNS. Na rede bridge padrão do Docker, esse anúncio nunca sai do Docker, então os celulares não o veem. Para que ele apareça, execute o contêiner na rede do host — o mapeamento `ports:` deixa de valer, e o Downtify escuta diretamente em `DOWNTIFY_PORT`:

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

Caso contrário, basta digitar o endereço do servidor no app (`http://<IP do host>:8000`); nada mais depende da descoberta.

## Porta personalizada

Se a porta 8000 já estiver em uso, mapeie outra porta do host e defina a variável de ambiente `DOWNTIFY_PORT` para que o contêiner escute internamente na mesma porta:

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

Você também pode escolher a porta em **Configurações → Servidor → Porta** em vez de definir `DOWNTIFY_PORT` (que, quando definida, prevalece sobre as Configurações). Na rede bridge padrão, mude o mapeamento `ports:` para a mesma porta e recrie o contêiner — veja [Mudando a porta](../features/server.md#changing-the-port).

## Com DNS personalizado (recomendado)

Alguns provedores de internet e redes corporativas bloqueiam o YouTube. Adicionar resolvedores DNS explícitos melhora a confiabilidade:

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

## Atualização

```bash
docker compose pull
docker compose up -d
```

Suas músicas e configurações são preservadas nos volumes.

## Volumes

| Caminho no arquivo compose | Finalidade |
|------------------------------|---------|
| `./downloads:/downloads` | Arquivos de áudio baixados (diretório local) |
| `downtify_data:/data` | Banco de dados e configurações do aplicativo (volume nomeado) |

Você pode trocar o volume nomeado por um caminho local (`./data:/data`) se preferir gerenciá-lo por conta própria.
