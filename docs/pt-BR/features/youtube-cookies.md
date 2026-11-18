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
      - ./cookies.txt:/cookies.txt
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Monte-o com permissão de escrita (sem `:ro`) para que a manutenção possa salvar os cookies renovados nele; um arquivo só de leitura continua sendo usado, mas fica velho como antes.

Quando ela está definida, a tela de configurações mostra a seção de cookies bloqueada e recusa envios e exclusões — a instalação é dona dessa configuração, e o Downtify não deve sobrescrever um arquivo que não gerencia. Remova a variável (e recrie o contêiner) para gerenciar os cookies pela interface web.

`DOWNTIFY_COOKIES_FROM_BROWSER` lê os cookies direto de um perfil de navegador, mas isso exige que o armazenamento de cookies do navegador esteja acessível *dentro* do contêiner, então raramente é utilizável no Docker.

## Mantendo-os funcionando

Cookies exportados não vencem numa data fixa. A sessão do Google é um conjunto de cookies que muda o tempo todo: a aba de onde eles saíram renova `__Secure-1PSIDTS`, `SIDCC` e companhia a cada poucos minutos, e uma cópia que nunca recebe os valores novos acaba recusada. O yt-dlp então registra "The provided YouTube account cookies are no longer valid". Numa VPN ou num IP de datacenter o YouTube é mais rígido, então isso pode acontecer em poucas horas.

O Downtify mantém o arquivo enviado conectado sozinho:

- **Cada download salva os valores novos.** O yt-dlp recebe uma cópia privada do arquivo a cada download; quando termina, os cookies que o YouTube mudou nesse meio-tempo voltam para o `cookies.txt` guardado, sem desfazer um valor mais novo que outro download salvou.
- **Uma manutenção os renova num intervalo.** A cada 15 minutos (`DOWNTIFY_COOKIES_REFRESH_MINUTES`, `0` desativa) o Downtify pede ao Google para renovar os cookies de sessão — a mesma requisição que o navegador faz —, abre o `youtube.com` com eles e salva o que mudou. Mesmo um servidor que passa dias sem baixar nada mantém a sessão viva.
- **A tela de configurações mostra o resultado.** **Configurações → Cookies do YouTube** mostra *Conectado*, *Desconectado*, *Sem conta* (o arquivo não tem sessão do Google, só cookies de visitante) ou *Falha na verificação*, quando foi a última verificação e quando o YouTube pediu verificação de bot pela última vez. *Verificar agora* roda a manutenção na hora. Um envio novo é verificado alguns segundos depois de salvo.

O que ainda fica com você:

- **Exporte de uma janela anônima e feche-a.** Entre no YouTube numa janela anônima, abra `youtube.com/robots.txt` nessa aba, exporte os cookies e feche a janela. Uma aba que você continua usando renova a sessão por conta própria, e a cópia do Downtify é desconectada em minutos. Se puder, não use a mesma conta numa janela normal ao mesmo tempo.
- **Envie um arquivo novo quando a tela disser *Desconectado*.** O Google ainda pode encerrar a sessão (troca de senha, "sair de todos os dispositivos", uma revisão de segurança). O log também avisa: `YouTube cookies are signed out`.
- Algumas regiões exigem verificação completa de identidade na conta Google antes de o YouTube entregar qualquer conteúdo com restrição de idade. Estar conectado nem sempre basta.

::: info Por que não há um botão "Entrar com o Google"
O Downtify não consegue entrar no Google por você. O Google bloqueia logins por script e em navegadores headless ("Este navegador ou app pode não ser seguro"), pede verificação em duas etapas e confirmação no celular, e o YouTube não aceita mais OAuth de clientes de terceiros como o yt-dlp. Um formulário de login no Downtify também significaria entregar a ele a sua senha do Google. Manter viva uma sessão exportada é a parte que dá para automatizar.
:::

::: tip Verificação de bot sem conta
"Sign in to confirm you're not a bot" vem do endereço IP, não da falta de cookies. Se aparece o tempo todo numa VPN, trocar o servidor ou o país de saída da VPN costuma ajudar mais que cookies novos. Cookies usados em muitos downloads também aumentam a chance de o YouTube limitar aquela conta, então uma conta descartável é a escolha mais segura.
:::

::: warning Trate o arquivo como uma senha
Um `cookies.txt` contém tokens de sessão ativos da sua conta Google. Qualquer pessoa que consiga lê-lo pode agir como você no YouTube. O Downtify o guarda com permissões só para o dono onde o sistema de arquivos permite e nunca expõe o conteúdo pela API — apenas se há um configurado, seu tamanho e quando mudou. Use uma conta Google descartável se preferir não arriscar a principal.
:::
