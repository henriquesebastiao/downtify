---
icon: lucide/share-2
---

# slskd e Navidrome

Duas integrações opcionais para bibliotecas auto-hospedadas:

- **[slskd](https://github.com/slskd/slskd)** — baixe faixas da rede Soulseek pelo seu próprio servidor slskd, como uma fonte de áudio extra ao lado do YouTube Music e do YouTube.
- **[Navidrome](https://www.navidrome.org/)** — espelhe as playlists que você baixa no Navidrome, para que apareçam em qualquer cliente Subsonic.

Ambas vêm desligadas por padrão e são configuradas em **Configurações**.

## Fontes de áudio e ordem de alternativas

**Configurações → Fontes de áudio** é uma lista ordenada. Toque em uma fonte para adicioná-la ou removê-la; com mais de uma selecionada, use as setas para reordená-las. Cada faixa tenta as fontes nessa ordem e para na primeira que fornece áudio:

| Fonte | O que faz |
|--------|-------------|
| **YouTube Music** | O padrão. Pesquisa no YouTube Music, recorrendo ao YouTube comum quando não há correspondência aceitável — veja [Como funciona](../how-it-works.md#fallback-to-standard-youtube). |
| **YouTube** | Pesquisa só no YouTube comum. |
| **slskd** | Pesquisa no Soulseek pelo slskd e baixa o arquivo que melhor corresponder. |

Ativar o slskd o coloca em primeiro na lista. Se o slskd acabar sendo a única fonte, o YouTube Music e o YouTube ainda são tentados depois dele, então uma faixa que o slskd não encontra ainda é baixada. A fila de downloads mostra qual fonte atendeu cada faixa.

## slskd

### Configuração

1. Execute o slskd e crie uma chave de API para o Downtify (veja a documentação do slskd).
2. Monte a pasta de downloads do slskd no contêiner do Downtify — a mesma pasta do host em que o slskd grava. Veja [Docker Compose → Com slskd](../getting-started/docker-compose.md#with-slskd-soulseek).
3. Em **Configurações → slskd (Soulseek)**, ative o slskd e preencha:
    - **URL do slskd** — por exemplo `http://slskd:5030` quando os dois contêineres compartilham uma rede Docker.
    - **Chave de API**.
    - **Pasta de downloads** — o caminho *dentro do contêiner do Downtify* em que essa pasta está montada (padrão `/slskd`), não o caminho do host.

Salvar é recusado com uma mensagem de erro se o slskd estiver ativado sem URL ou chave de API.

### Testando a conexão

Pressione **Testar conexão** sob os campos para verificá-los antes de salvar — ele usa o que está digitado no formulário, salvo ou não, e não altera nada. Ele informa:

| Resultado | O que significa |
|--------|---------------|
| **Conectado ao slskd 0.21.4.** | O endereço está certo e a chave de API foi aceita |
| **O slskd está conectado ao Soulseek.** / **não está conectado** | Se o próprio slskd está conectado à rede Soulseek. Se não estiver, as buscas não acham nada até que esteja — um aviso, já que as configurações em si estão certas |
| **O Downtify consegue ler `/slskd`.** / **não consegue ler** | Se a pasta de downloads acima existe dentro *deste* contêiner e é legível. A causa usual de um aviso é uma pasta que não está montada — veja [Configuração](#setup) |
| **O slskd recusou a chave de API.** | O servidor respondeu, mas não a esta chave |
| **Não foi possível alcançar … / não respondeu a tempo.** | Endereço ou porta errados, o servidor está fora do ar ou não é alcançável a partir do contêiner do Downtify |
| **Não parece ser o slskd.** | Algo respondeu, mas não o slskd — muitas vezes uma porta errada, ou um caminho base faltando no endereço |
| **O certificado HTTPS não é confiável.** | Use `http://` na sua própria rede, ou um certificado de uma autoridade confiável; o Downtify não ignora a verificação de certificados |

Editar qualquer campo limpa o último resultado, já que ele não descreve mais o que está no formulário. O botão fica desativado até o endereço e a chave estarem preenchidos.

### Como uma faixa é associada

O Downtify pesquisa no slskd com o título e o artista da faixa e classifica os resultados pela proximidade do nome do arquivo e da duração com a faixa. Entre correspondências igualmente boas, prefere MP3 e depois FLAC, e ignora arquivos que informam bitrate abaixo de 256 kbps. Tenta até cinco candidatos, um após o outro. Quando uma transferência termina, o Downtify confere as tags e a duração do arquivo com a faixa antes de mantê-lo.

Se nada aceitável aparecer, a transferência não terminar dentro do **Tempo limite total**, ou ficar na fila do par remoto sem progresso por mais que o **Tempo limite na fila**, o Downtify passa para a próxima fonte de áudio.

### Deixar os arquivos no lugar

Com **Deixar os arquivos do slskd no lugar** ligado (o padrão), o arquivo baixado fica na pasta do slskd: o Downtify grava nele ali mesmo os metadados, a capa e a letra e o registra na biblioteca com um caminho `slskd/…`. A Biblioteca, o player e os arquivos M3U usam esse caminho, e ele é servido por `/media/slskd/…`.

Desligue para copiar o arquivo ao lado dos seus outros downloads, seguindo o seu modelo de nome de arquivo e as configurações de [organização de arquivos](file-organization.md).

::: info
Os arquivos do slskd mantêm o formato original — não são transcodificados para o formato escolhido em Configurações.
:::

## Navidrome

### Configuração

1. Garanta que a pasta de música do Navidrome inclua a pasta de downloads do Downtify (e a pasta do slskd, se você deixar os arquivos do slskd no lugar). O Navidrome só consegue adicionar faixas a uma playlist depois de varrê-las.
2. Em **Configurações → Navidrome**, ative o Navidrome e informe a URL, o usuário e a senha dele.
3. Opcionalmente, adicione um usuário e uma senha de **admin**. O Downtify então pede ao Navidrome que varra a biblioteca antes de associar faixas novas, em vez de esperar a varredura agendada do próprio Navidrome.

### Testando a conexão

Pressione **Testar conexão** sob os campos para verificá-los antes de salvar — ele usa o que está digitado no formulário, salvo ou não, e não altera nada. Ele informa:

| Resultado | O que significa |
|--------|---------------|
| **Conectado ao navidrome 0.53.3.** | O endereço está certo e o usuário e a senha foram aceitos |
| **Esta conta pode iniciar varreduras da biblioteca.** | A conta usada para varreduras é admin. É o usuário admin que você preencheu, ou o normal quando você o deixou vazio |
| **Esta conta não pode iniciar varreduras da biblioteca.** | O Navidrome só deixa admins iniciarem uma varredura, e não avisa quando o Downtify tenta — as músicas novas simplesmente aparecem tarde. Preencha um usuário e uma senha de admin |
| **A conta de admin não é admin.** | O login de admin informado funciona, mas pertence a um usuário comum |
| **O Navidrome recusou o usuário ou a senha de admin.** | O login da conta de varredura está errado; o login principal é informado separadamente |
| **O Navidrome recusou o usuário ou a senha.** | O servidor respondeu, mas não a este login |
| **Não foi possível alcançar … / não respondeu a tempo.** | Endereço ou porta errados, o servidor está fora do ar ou não é alcançável a partir do contêiner do Downtify |
| **Não parece ser o Navidrome.** | Algo respondeu, mas não a API Subsonic — muitas vezes uma porta errada, ou uma URL base faltando no endereço |
| **O certificado HTTPS não é confiável.** | Use `http://` na sua própria rede, ou um certificado de uma autoridade confiável; o Downtify não ignora a verificação de certificados |

Os direitos de varredura só são consultados — o teste nunca inicia uma varredura. Editar qualquer campo limpa o último resultado, e o botão fica desativado até o endereço, o usuário e a senha estarem preenchidos.

::: info Nada é enviado de volta à página
A resposta traz só o que foi encontrado — uma versão, um caminho, um status — nunca a sua senha nem a requisição que o Downtify fez.
:::

### Sincronização de playlists

O espelhamento é configurado por admins (Configurações → Navidrome); contas comuns não podem criar espelhos, embora os downloads delas sejam espelhados como os de qualquer outra pessoa quando a integração está ligada.

Com **Criar playlists no Navidrome** ligado, o Downtify cria (ou atualiza) uma playlist do Navidrome com o mesmo nome depois de:

- um download de playlist do Spotify terminar,
- uma varredura do [Monitor de playlists](playlist-monitor.md) adicionar faixas,
- faixas serem excluídas da Biblioteca, ou os [caminhos da biblioteca serem corrigidos](library-catalog.md#fix-library-paths).

As faixas são associadas às músicas do Navidrome primeiro pelo caminho, depois pelas tags. **Tornar públicas as playlists do Navidrome** controla a visibilidade da playlist no Navidrome.

::: warning Arquivos cujas tags não correspondem à playlist são excluídos
Quando uma playlist é atualizada (depois de exclusões, **Corrigir caminhos da biblioteca** ou **Baixar o que falta** numa playlist já completa), um arquivo da biblioteca registrado para uma faixa do Spotify é **excluído do disco** se o título/artista embutido claramente não corresponder àquela faixa — o Downtify o trata como um download errado. Tenha isso em mente se você edita tags à mão.
:::

### Capa da playlist

Nada a configurar: com [Salvar a capa da playlist](playlist-cover-art.md) ligado, o Navidrome pega o `.jpg` que o Downtify grava ao lado do M3U da playlist como uma **imagem auxiliar (sidecar)** — a forma dele de resolver a arte de playlists — desde que a pasta de música dele cubra esse arquivo. O Downtify não faz nenhuma chamada de API para isso.

## Downloads de playlists

A página **Biblioteca** lista as playlists do Spotify que você baixou pelo Downtify em **Downloads de playlists**. Expanda para ver, para cada playlist, quantas faixas estão na sua biblioteca em relação à lista atual de faixas do Spotify. A partir dali você pode:

- **Baixar o que falta** — enfileira só as faixas que ainda não estão na sua biblioteca.
- **Tocar** as faixas já baixadas.
- Expandir uma playlist para ver e baixar faixas ausentes individualmente.
- **Excluir** a playlist — veja abaixo.

### Excluindo uma playlist

Excluir uma playlist (por este painel, ou com **Excluir playlist** ao lado do filtro de playlists da Biblioteca) remove do disco toda faixa registrada nela — **inclusive faixas que outras playlists também contêm** — além do arquivo M3U e da [capa](playlist-cover-art.md) salva ao lado, e deixa de acompanhá-la. As outras playlists que compartilhavam essas faixas têm o M3U e a playlist do Navidrome reescritos em segundo plano.
