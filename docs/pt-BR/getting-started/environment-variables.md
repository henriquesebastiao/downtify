---
icon: lucide/settings
---

# Variáveis de ambiente

Todas as variáveis de ambiente são opcionais. O Downtify funciona de imediato sem nenhuma delas.

## Essenciais

| Variável | Padrão | Descrição |
|----------|---------|-------------|
| `DOWNTIFY_PORT` | _(não definida)_ | Porta em que o servidor escuta (dentro do contêiner). Não definida: a porta escolhida em **Configurações → Servidor → Porta**, ou então `8000`. Definida, ela prevalece e o campo das Configurações fica bloqueado. Mude o lado esquerdo do mapeamento de portas para expor outra porta do host. Veja [Mudando a porta](../features/server.md#changing-the-port). |
| `DOWNLOAD_DIR` | `/downloads` | Diretório onde os arquivos de áudio são salvos. Altere se você montar a biblioteca em outro caminho. |
| `HOST` | `0.0.0.0` | Endereço de escuta do servidor web. |
| `DOWNTIFY_LOG_LEVEL` | `info` | Nível de log da aplicação (`debug`, `info`, `warning`, …). |
| `TZ` | `UTC` | Fuso horário local (nome IANA, por exemplo `America/Sao_Paulo`), usado para interpretar `DOWNTIFY_MONITOR_SYNC_TIME` abaixo. |

## Monitor de playlists

| Variável | Padrão | Descrição |
|----------|---------|-------------|
| `DOWNTIFY_MONITOR_SYNC_TIME` | _(não definida)_ | Hora do dia (`HH:MM` em 24h, no fuso de `TZ` acima) em que as sincronizações do [Monitor de playlists](../features/playlist-monitor.md#choosing-a-daily-sync-time) com intervalo de um dia ou mais (todo dia, semana, 2 semanas, mês) devem rodar. Deixe sem definir para sincronizar exatamente um intervalo depois da verificação anterior, seja qual for o horário em que isso cair. |

```yaml
environment:
  - TZ=America/Sao_Paulo
  - DOWNTIFY_MONITOR_SYNC_TIME=03:00
```

## Apps para celular e login

Veja [Apps para celular](../features/mobile-apps.md) e [Usuários e login](../features/users.md). O login é obrigatório, a menos que `DOWNTIFY_DISABLE_AUTH` seja `true`; `DOWNTIFY_REQUIRE_SIGN_IN` de versões anteriores não é mais usada (um aviso é registrado no log enquanto ela estiver definida).

| Variável | Padrão | Descrição |
|----------|---------|-------------|
| `DOWNTIFY_DISABLE_AUTH` | `false` | `true` desliga as contas: ninguém faz login, e quem alcançar o servidor o usa como administrador. A página de login, os botões de sair, **Configurações → Usuários** e a parte de conta de **Configurações → Geral** desaparecem. Os apps pareados continuam funcionando. Volte para `false` (ou remova-a) e o login volta a ser exigido, com as contas como estavam. Veja [Usuários e login](../features/users.md#turning-accounts-off). |
| `DOWNTIFY_TRUSTED_PROXIES` | _(não definida)_ | Endereços ou redes do seu proxy reverso, separados por vírgula (por exemplo `172.18.0.0/16,10.0.0.5`). Só as requisições vindas deles têm os cabeçalhos `X-Forwarded-For`, `X-Forwarded-Proto` e `X-Forwarded-Host` aceitos — para o endereço do cliente pelo qual as tentativas de login e de pareamento são limitadas, a flag secure do cookie de login e a verificação de mesma origem. Não definida: esses cabeçalhos são ignorados. |
| `DOWNTIFY_DISCOVERY` | `true` | `false` para de anunciar o servidor na rede local (mDNS, `_downtify._tcp`), que os apps usam para listá-lo em *Encontrados nesta rede*. Na rede bridge do Docker o anúncio não chega à LAN de qualquer forma — veja [Docker Compose](docker-compose.md#finding-the-server-from-the-apps). |
| `DOWNTIFY_TRANSCODE_CACHE_MB` | `2048` | Maior tamanho, em MB, em que o cache de cópias transcodificadas (`/data/transcode_cache`) é mantido; as cópias tocadas há mais tempo saem primeiro. |
| `DOWNTIFY_TRANSCODE_CONCURRENCY` | `2` | Quantas músicas são transcodificadas ao mesmo tempo para as qualidades de streaming menores dos apps. |
| `DOWNTIFY_STREAM_CACHE_MB` | `1024` | Maior tamanho, em MB, em que o cache de áudio transmitido (`/data/stream_cache`) é mantido; as cópias tocadas há mais tempo saem primeiro. Transmitir pelo servidor é o que toca faixas não baixadas onde o próprio navegador não alcança o YouTube. |
| `DOWNTIFY_STREAM_CONCURRENCY` | `2` | Quantos downloads de streaming podem rodar ao mesmo tempo. |

## Lixeira de músicas

Veja [Lixeira de músicas](../features/music-trash.md). Desligada, a menos que uma destas esteja definida.

| Variável | Padrão | Descrição |
|----------|---------|-------------|
| `DOWNTIFY_TRASH` | `false` | `true` liga a lixeira de músicas para a pasta de downloads: remover músicas as move para uma lixeira guardada por 30 dias, e o próprio Downtify move os arquivos. Enquanto ela está ligada, só administradores removem músicas. |
| `DOWNTIFY_TRASH_CONFIG` | _(não definida)_ | Caminho, dentro do contêiner, de um arquivo JSON com as pastas que a lixeira cobre e onde o worker dela roda (`embedded` ou `external`). Prevalece sobre `DOWNTIFY_TRASH`. Um arquivo que não pode ser lido impede o servidor de iniciar. Veja [O arquivo de configuração](../features/music-trash.md#the-configuration-file). |

## Verificação de saúde

A imagem tem um [`HEALTHCHECK` do Docker](https://docs.docker.com/reference/dockerfile/#healthcheck) integrado — não é preciso um `--health-cmd` próprio. Ele consulta `GET /api/health` na porta do próprio contêiner a cada 30 segundos (timeout de 5 segundos, carência de 20 segundos na inicialização, 3 tentativas antes de marcar o contêiner como não saudável). `docker ps` e `docker inspect` mostram o resultado, e ferramentas como o `condition: service_healthy` do Compose ou o Watchtower podem agir com base nele.

| Variável | Padrão | Descrição |
|----------|---------|-------------|
| `DOWNTIFY_HEALTHCHECK` | `1` | Defina como `0` para desativar a verificação integrada — ela passa a informar sempre "saudável" sem contatar o servidor. Use se uma verificação externa/do orquestrador (por exemplo, uma liveness probe do Kubernetes) deve ser a única a decidir a saúde do contêiner. |

```yaml
environment:
  - DOWNTIFY_HEALTHCHECK=0
```

## Anti-bot / YouTube

O YouTube desafia periodicamente baixadores automatizados. Estas variáveis dão saídas de emergência quando os padrões deixam de funcionar.

| Variável | Padrão | Descrição |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(não definida)_ | Defina como `1` para forçar o yt-dlp a usar só IPv4. Útil quando o seu host tem um endereço IPv6 quebrado ou limitado. |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | Lista, separada por vírgulas, dos clientes de player do yt-dlp a tentar, em ordem. A lista padrão do Downtify já favorece clientes que funcionam sem um runtime de JavaScript. Altere só se você souber que um cliente específico está sendo bloqueado. |
| `DOWNTIFY_YT_PO_TOKEN` | _(não definida)_ | Tokens Proof-of-Origin para o yt-dlp, separados por vírgulas, cada um no formato `<client>.<context>+<token>` (por exemplo `mweb.gvs+ABC123`). Necessários só se o YouTube passar a exigir PO Tokens para os clientes que você usa. |
| `DOWNTIFY_COOKIES_FILE` | _(não definida)_ | Caminho de um `cookies.txt` em formato Netscape **dentro do contêiner**. Permite ao yt-dlp se autenticar como uma sessão real de navegador — necessário para faixas explícitas/com restrição de idade e sempre que o YouTube impõe uma barreira de login. Tem precedência sobre um arquivo enviado na interface web e deixa essa seção da interface somente leitura. Veja [Cookies do YouTube](../features/youtube-cookies.md). |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(não definida)_ | Nome do navegador de onde extrair os cookies (por exemplo `chrome`, `firefox`). Exige que o armazenamento de cookies do navegador esteja acessível dentro do contêiner, então raramente é utilizável no Docker. |

::: tip Você provavelmente não precisa delas
Você pode enviar um `cookies.txt` direto em **Configurações → Cookies do YouTube** na interface web. Ele fica guardado em `/data` (então sobrevive às atualizações do contêiner), não precisa de bind mount nem de caminho no contêiner e funciona igual no Windows, macOS e Linux. As variáveis acima continuam aceitas para instalações que preferem gerenciar o arquivo por conta própria.
:::

## Exemplo: Docker Compose com configurações anti-bot

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_FORCE_IPV4=1
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
    restart: unless-stopped
```

## Obtendo um cookies.txt

Use uma extensão de navegador como [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome) ou [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox). Exporte do `youtube.com` conectado a uma conta Google real e depois envie o arquivo em **Configurações → Cookies do YouTube** ou monte-o no contêiner como mostrado acima.

Veja [Cookies do YouTube](../features/youtube-cookies.md) para o passo a passo completo e [Solução de problemas](../troubleshooting.md) quando os downloads ainda falharem.

::: warning
Mantenha o seu `cookies.txt` privado — ele contém tokens de sessão que dão acesso à sua conta Google.
:::
