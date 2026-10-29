---
icon: lucide/cookie
---

# Cookies do YouTube

O Downtify busca o áudio no YouTube. Na maior parte do tempo isso funciona de forma anônima — mas nem sempre:

- **Faixas explícitas / com restrição de idade.** O YouTube só as entrega a uma conta de adulto conectada. Sem cookies, o download falha.
- **Desafios anti-bot.** Em IPs de datacenter (VPS, algumas VPNs), o YouTube periodicamente responde com "Faça login para confirmar que você não é um robô" em vez de áudio.

Fornecer um `cookies.txt` resolve os dois: o yt-dlp passa a falar com o YouTube como a sua sessão conectada no navegador.

## Enviando um cookies.txt (recomendado)

1. Instale uma extensão de exportação de cookies: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge) ou [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
2. Abra o `youtube.com` **conectado à sua conta Google** e exporte os cookies desse site — o arquivo precisa estar no formato **Netscape**
3. No Downtify, abra **Configurações** (⚙️) → **Cookies do YouTube** → **Enviar cookies.txt**

O arquivo é validado no envio — um arquivo que não seja um cookie jar Netscape é recusado na hora, em vez de quebrar em silêncio todos os downloads seguintes. Se ele não contiver cookies de `youtube.com` ou `google.com`, você recebe um aviso, pois isso geralmente significa que foi exportado da aba errada.

Depois de enviado, você pode **substituí-lo** (enviando outro arquivo) ou **excluí-lo** na mesma tela.

::: tip Este é o caminho que serve para qualquer plataforma
Enviar pela interface web não exige bind mounts, caminhos de arquivo nem shell — e é isso que faz funcionar no Docker Desktop para Windows, onde montar um `cookies.txt` no contêiner é notoriamente chato.
:::

## Onde fica guardado

O arquivo enviado é gravado como `cookies.txt` dentro do diretório de dados do Downtify (`/data` por padrão) — o mesmo volume que guarda o `settings.json` e o banco de dados do Monitor de playlists. Por isso ele **sobrevive às atualizações do contêiner**: baixar uma nova imagem e recriar o contêiner mantém seus cookies, desde que `/data` continue sendo um volume nomeado ou um bind mount.

## Usando uma variável de ambiente

A variável [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube), que já existia, continua funcionando e **tem precedência**:

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Quando ela está definida, a tela de configurações mostra a seção de cookies bloqueada e recusa envios e exclusões — a instalação é dona dessa configuração, e o Downtify não deve sobrescrever um arquivo que não gerencia. Remova a variável (e recrie o contêiner) para gerenciar os cookies pela interface web.

`DOWNTIFY_COOKIES_FROM_BROWSER` lê os cookies direto de um perfil de navegador, mas isso exige que o armazenamento de cookies do navegador esteja acessível *dentro* do contêiner, então raramente é utilizável no Docker.

## Mantendo-os funcionando

- Os cookies expiram. Se os downloads com restrição de idade voltarem a falhar, exporte um arquivo novo e envie-o como substituto.
- Exportar de uma **janela privada/anônima** que você depois fecha produz uma sessão de vida mais longa, porque fechar uma janela normal pode invalidar a sessão exportada.
- Algumas regiões exigem verificação completa de identidade na conta Google antes de o YouTube entregar qualquer conteúdo com restrição de idade. Estar conectado nem sempre basta.

::: warning Trate o arquivo como uma senha
Um `cookies.txt` contém tokens de sessão ativos da sua conta Google. Qualquer pessoa que consiga lê-lo pode agir como você no YouTube. O Downtify o guarda com permissões só para o dono onde o sistema de arquivos permite e nunca expõe o conteúdo pela API — apenas se há um configurado, seu tamanho e quando mudou. Use uma conta Google descartável se preferir não arriscar a principal.
:::
