---
icon: lucide/life-buoy
---

# Solução de problemas

Problemas comuns e o que os resolve. A maioria das falhas de download se resume a uma das duas primeiras entradas.

## Uma faixa com conteúdo explícito não baixa

**Sintoma** — o download falha e a fila mostra uma mensagem sobre a faixa ter restrição de idade, ou (em versões antigas) um erro bruto como:

```
Error: ERROR: [youtube] <id>: Sign in to confirm your age.
This video may be inappropriate for some users.
```

**Causa** — o YouTube só entrega faixas com restrição de idade (explícitas) a uma conta de adulto conectada. O Downtify baixa de forma anônima por padrão, então o YouTube recusa.

**Solução** — forneça cookies do YouTube: **Configurações** (⚙️) → **Cookies do YouTube** → **Enviar cookies.txt**. Veja [Cookies do YouTube](features/youtube-cookies.md) para saber como exportar o arquivo.

Se ainda falhar com cookies configurados, os cookies estão velhos ou a própria conta não concluiu a verificação de idade do Google. Exporte um arquivo novo de um navegador conectado a uma conta verificada e envie de novo.

## Os downloads falham, expiram ou nunca começam

**Sintoma** — downloads falham para faixas aparentemente comuns, às vezes com "Faça login para confirmar que você não é um robô" ou um erro de formato/extração.

**Causa** — o YouTube limita e desafia requisições que considera automatizadas. Isso é muito mais comum em um VPS ou atrás de uma VPN do que em uma conexão doméstica.

**Solução**, em ordem de quanto costuma ajudar:

1. **Envie um `cookies.txt`** ([Cookies do YouTube](features/youtube-cookies.md)). Uma sessão autenticada é desafiada bem menos vezes. É a correção mais eficaz.
2. **Adicione uma pausa entre os downloads** — **Configurações** → *Pausa entre downloads* (tente 5–15 s) e reduza os *Downloads simultâneos*. Bombardear o YouTube com uma playlist inteira de uma vez é o que dispara a limitação.
3. **Force IPv4** — defina `DOWNTIFY_FORCE_IPV4=1` se o seu host anuncia IPv6 mas não consegue roteá-lo de fato (aparece como erros de DNS/`EAI_AGAIN`).
4. **Atualize a imagem** — `docker compose pull && docker compose up -d`. O YouTube muda as defesas com frequência e cada versão traz um `yt-dlp` mais novo.

## Um cookies.txt no Windows / Docker Desktop não é reconhecido

**Sintoma** — `DOWNTIFY_COOKIES_FILE` está definido, mas o Downtify se comporta como se não houvesse cookies.

**Causa** — o caminho é um caminho *do contêiner*. Um caminho do Windows como `C:\Users\me\cookies.txt` não significa nada dentro do contêiner, e o arquivo precisa ser montado antes que a variável possa apontar para ele.

**Solução** — dispense a variável por completo e envie o arquivo em **Configurações** → **Cookies do YouTube**. Esse caminho não precisa de montagens e funciona igual em todas as plataformas.

Se preferir manter a variável, monte o arquivo e aponte para o destino da montagem, não para o caminho no host:

```yaml
volumes:
  - ./cookies.txt:/cookies.txt:ro
environment:
  - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

## O botão de envio de cookies está esmaecido

`DOWNTIFY_COOKIES_FILE` está definido, então essa instalação gerencia o próprio arquivo de cookies e a interface web fica somente leitura de propósito. Remova a variável (e recrie o contêiner) para gerenciar os cookies pela interface.

## Os cookies enviados sumiram depois de atualizar o contêiner

O arquivo enviado fica no diretório de dados do Downtify (`/data`). Se esse diretório não for um volume nomeado ou um bind mount, tudo o que há nele — configurações e o banco de dados do Monitor de playlists incluídos — se perde quando o contêiner é recriado:

```yaml
volumes:
  - ./downloads:/downloads
  - downtify_data:/data   # ← mantenha isto
```

## "cookies.txt is invalid" ao enviar

O Downtify valida o arquivo no envio. Ele precisa ser um cookie jar **Netscape**: um cookie por linha, campos separados por tabulações, opcionalmente com comentários `#`. Uma exportação em JSON, uma planilha ou um cabeçalho `Cookie:` copiado são recusados.

Use uma extensão de navegador que exporte no formato Netscape (veja [Cookies do YouTube](features/youtube-cookies.md)) e exporte com a aba em `youtube.com`.

## Uma playlist baixa de novo faixas que eu já tenho

O Downtify registra todas as faixas baixadas automaticamente em seu banco de dados, então mover arquivos para outro lugar do disco não dispara um novo download. Uma faixa só é baixada de novo depois que uma verificação de hora em hora encontra o arquivo realmente ausente do diretório de downloads. Veja [Monitor de playlists](features/playlist-monitor.md#how-it-works).

Se os arquivos somem a cada reinício, o volume `/downloads` não está persistido — mesma solução acima.

## "Could not find a YouTube match for '…'"

Nem o YouTube Music nem o YouTube comum devolveram um resultado que passasse nas verificações do comparador — título parecido com o original, ao menos um artista em comum, não ser versão de karaokê/cover/ao vivo/em outro idioma e duração a até 30 segundos da do Spotify. Veja [Como funciona](how-it-works.md#fallback-to-standard-youtube).

Isso geralmente significa que a música realmente não está no YouTube, ou só foi enviada com um título ou crédito de artista muito diferente. Se você encontrar o vídeo certo por conta própria, cole a URL dele do YouTube na barra de busca para baixar exatamente aquele vídeo.

## O áudio baixado tem metadados ou capa errados

O Downtify obtém os metadados do Spotify e casa o áudio no YouTube Music. Uma divergência geralmente significa que a correspondência caiu em um cover, remix ou versão ao vivo. Baixar pelo link do **álbum** do Spotify, em vez de um resultado de busca, dá muito mais informação ao comparador (número da faixa, álbum, tipo de lançamento).

## Ainda com problemas?

Abra uma issue em [github.com/henriquesebastiao/downtify/issues](https://github.com/henriquesebastiao/downtify/issues) com:

- a versão do Downtify (mostrada no fim da barra lateral e em **Configurações → Sobre**),
- os logs do contêiner em torno da falha (`docker compose logs downtify`),
- e se há cookies configurados.
