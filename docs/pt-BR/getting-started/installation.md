---
icon: lucide/download
---

# Instalação

O jeito mais rápido de rodar o Downtify é com um único comando `docker run`. Não é preciso Python, Node.js nem outras dependências do sistema no host — tudo vem dentro da imagem.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado e em execução

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

Troque `/path/to/music` pelo diretório onde você quer guardar suas músicas.

Quando o contêiner iniciar, abra **[http://localhost:8000](http://localhost:8000)** no navegador.

## Volumes

| Volume | Finalidade |
|--------|---------|
| `/downloads` | Arquivos de áudio baixados |
| `/data` | Banco de dados do aplicativo e configurações persistentes |

Os dois volumes persistem entre reinícios e atualizações do contêiner. O volume `/downloads` pode ser qualquer diretório da sua máquina host ou um volume Docker nomeado.

## Porta personalizada

Para expor o Downtify em outra porta do host, mude o lado esquerdo do `-p`:

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # host:contêiner
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Depois abra **[http://localhost:9090](http://localhost:9090)**.

## Atualização

Baixe a imagem mais recente e recrie o contêiner:

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Suas músicas e configurações são preservadas nos volumes.

## E agora?

- **[Docker Compose](docker-compose.md)** — jeito mais fácil de gerenciar o contêiner a longo prazo
- **[Variáveis de ambiente](environment-variables.md)** — ajuste o comportamento anti-bot e outras opções avançadas
- **[Configurações de download](../features/download-settings.md)** — escolha o formato e a taxa de bits
