---
icon: lucide/replace
---

# Substituir áudio

O Downtify escolhe automaticamente o áudio de cada música, e às vezes escolhe o errado: outra música com o mesmo nome, uma versão ao vivo, um remix ou um upload com uma introdução longa. **Substituir áudio** permite escolher à mão a versão certa. A faixa mantém seu lugar em todos os lugares — suas playlists, arquivos M3U, curtidas e apps pareados — e só o áudio muda.

Só os administradores podem substituir áudio (veja [Usuários e login](users.md#admins-and-users)).

## Substituindo o áudio de uma faixa

1. Na **Biblioteca**, abra o menu da faixa (botão direito, ou o botão **⋯**) e escolha **Substituir áudio…**.
2. O Downtify busca "Artista - Título" no **YouTube Music** e no **YouTube** e lista o que encontra. Altere a busca, ou cole o link de um vídeo ou música do YouTube ou YouTube Music, para obter exatamente o upload que você quer.
3. Escolha uma versão. Cada uma mostra de onde vem e quanto dura, ao lado da duração do seu arquivo. Uma versão com diferença de até 3 segundos em relação ao seu arquivo fica destacada. O botão ↗ a abre no YouTube, para você ouvir antes de escolher.
4. Clique em **Substituir áudio**. A substituição roda como um download: mostra o progresso na janela e na **Fila**, e a janela avisa quando termina.

Se falhar (o vídeo está indisponível, ou o YouTube pede login — veja [Cookies do YouTube](youtube-cookies.md)), seu arquivo fica exatamente como estava. **Tentar de novo** na Fila tenta o mesmo vídeo outra vez, e colar outro link ali substitui por esse.

## Usar um arquivo do seu dispositivo

Se a versão certa não estiver no YouTube (um rip de CD, um download do Soulseek, um arquivo que alguém te mandou), use o seu próprio arquivo:

1. No diálogo, em **Ou use um arquivo do seu dispositivo**, toque em **Escolher um arquivo…** e escolha o arquivo de áudio.
2. Toque em **Substituir áudio**. O arquivo é enviado, verificado como áudio legível e recebe as tags do arquivo antigo.

Um arquivo no formato da própria faixa (um `.mp3` para um `.mp3`) é usado exatamente como está. Outro formato (`.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`, `.wav`, `.aiff`, `.aac` ou `.webm`) é convertido para o formato da faixa com a taxa de bits escolhida em [Configurações de download](download-settings.md), então use o mesmo formato quando tiver. Funciona também no modo só biblioteca, já que nada é buscado na internet.

## Os downloads deixam um arquivo substituído em paz

Com **Baixar de novo se o arquivo existir** ativado, um download posterior da mesma música (de outra playlist monitorada, do acompanhamento de um artista ou do download de uma playlist) gravaria por cima da sua substituição o que a busca automática encontrar. Por isso o Downtify lembra cada arquivo cujo áudio você substituiu, de qualquer forma, e esse download o conta como já baixado. [Melhorar biblioteca](library-upgrade.md) também não troca o áudio dele; capa, letras e tags ainda podem ser melhoradas.

O diálogo mostra quando o áudio de uma faixa foi substituído manualmente. **Deixar os downloads substituírem** desfaz isso para esse arquivo.

## O que permanece igual

- **O arquivo.** O novo áudio é gravado no mesmo caminho, no mesmo formato: um `.mp3` continua MP3 (na taxa de bits escolhida em [Configurações de download](download-settings.md)), um `.flac` continua FLAC, e assim por diante. Assim, toda playlist, arquivo M3U, música curtida, entrada do Navidrome e app pareado que aponta para o arquivo continua apontando.
- **As tags.** Título, artistas, álbum, número da faixa, ano, capa, letras incorporadas e todas as outras tags são copiadas do arquivo antigo para o novo áudio como estão. O arquivo auxiliar `.lrc` não é tocado. As letras sincronizadas foram cronometradas para o áudio antigo: se a nova versão começa em outro ponto, elas podem ficar fora de compasso.
- **A data.** O arquivo mantém a data de modificação, para não pular para o topo de "Adicionados recentemente".

Só arquivos `.mp3`, `.flac`, `.m4a`, `.ogg` e `.opus` — os formatos que o Downtify grava — podem ser substituídos.

## Como funciona

O vídeo escolhido é baixado ao lado do arquivo com um nome temporário que a biblioteca ignora (`<nome>.downtify-upgrade.<ext>`), convertido para o formato do arquivo, verificado como áudio legível, recebe as tags do arquivo antigo e só então é movido por cima do antigo. A API está na [referência da API](../api-reference.md#get-apilibraryreplacecandidates).
