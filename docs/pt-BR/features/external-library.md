---
icon: lucide/folder-plus
---

# Pastas de músicas existentes

A Biblioteca do Downtify é montada a partir dos arquivos que ele baixou — mais as **pastas extras** que você indicar. Essas pastas não são copiadas para `/downloads`. O Downtify lê as tags de cada arquivo (título, artista, álbum, número da faixa, ano), ignora as músicas que você já tem e organiza o resto sob o artista correspondente na Biblioteca e no player.

## Adicionar pastas

1. Monte a pasta do host no contêiner (Docker). O caminho que você digita nas Configurações é o **de dentro do contêiner**, a mesma regra da [pasta de download do slskd](slskd-navidrome.md).
2. Abra **Configurações → Biblioteca**.
3. Em **Pastas de músicas existentes**, adicione um ou mais caminhos (por exemplo, `/music/collection`). O campo sugere diretórios conforme você digita.
4. Clique em **Salvar** se quiser mantê-las sem sincronizar ainda, ou em **Sincronizar pastas** — isso salva a lista e faz a varredura imediatamente.

```yaml
services:
  downtify:
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

Então a pasta nas Configurações é `/music/collection`.

::: warning Os arquivos ficam onde estão
A sincronização não copia arquivos para `/downloads`. Quando a pasta é gravável, ela **grava** nesses arquivos os mesmos extras que um download gravaria: letras (e um arquivo auxiliar `.lrc` — ao lado do arquivo ou na pasta escolhida nas Configurações), uma capa se o arquivo não tiver nenhuma, e o gênero do iTunes quando possível. Uma sincronização posterior grava um arquivo auxiliar ausente mesmo que as letras já estejam nas tags, e **move** um `.lrc` existente para o local escolhido atualmente nas Configurações quando esse arquivo de origem é gravável. Excluir uma faixa pela Biblioteca continua excluindo o arquivo em disco.
:::

::: tip Montagens somente leitura
Monte a coleção com `:ro` se não quiser que o Downtify regrave os MP3s. A sincronização continua indexando-os. Coloque os arquivos `.lrc` na [pasta de letras](lyrics.md#sidecar-lrc-file) (desative **Guardar .lrc na mesma pasta do áudio**). As capas ausentes são salvas em `/data/cover_cache` (o endpoint de capas da Biblioteca), não no MP3. O gênero do iTunes é guardado no banco de metadados da biblioteca do Downtify, não no arquivo. Um `.lrc` que já está ao lado de um arquivo somente leitura é **copiado** para a pasta de letras e deixado onde está.
:::

## O que a sincronização faz

1. Percorre cada pasta configurada em busca de áudio reproduzível (os mesmos formatos do resto da biblioteca: MP3, M4A, FLAC, OGG, WAV, AAC, OPUS).
2. Lê as tags incorporadas. Um arquivo sem título/artista recorre a `Artista - Título` no nome do arquivo, como nas outras linhas da biblioteca.
3. **Ignora** um arquivo quando a biblioteca já tem aquela música (mesmo artista + título, e duração com diferença de poucos segundos quando ambas são conhecidas) — seja ela baixada pelo Downtify ou vinda de outra pasta extra.
4. **Associa artistas** aos nomes já existentes na biblioteca (`The Beatles` e `Beatles` viram um só artista). Nomes que não correspondem a um artista conhecido aparecem como um novo artista. Os novos artistas entram na fila para o mesmo preenchimento de perfil (foto/bio, quando essas configurações estão ativadas) que um download concluído.
5. **Etiqueta como um download** quando a pasta é gravável. Para cada faixa importada, usa os mesmos provedores de letras, a mesma busca de capa (só quando o arquivo não tem arte) e a mesma busca de gênero no iTunes que um download usaria. As letras vão para o arquivo; um arquivo auxiliar `.lrc` é gravado ao lado do áudio ou na [pasta de letras](lyrics.md#sidecar-lrc-file) escolhida nas Configurações. Capa e gênero seguem as [Configurações de download](download-settings.md) (`download_cover_art`, `download_lyrics`). Em uma montagem **somente leitura**, o MP3 não é regravado: uma capa ausente é guardada em `/data/cover_cache`, o gênero é guardado no catálogo da biblioteca, e os arquivos `.lrc` vão para a pasta de letras se você escolheu uma. As buscas rodam em lotes de **Downloads simultâneos**; uma **Pausa entre a sincronização** em Configurações → Downloads e arquivos espera entre esses lotes para que pastas grandes não esbarrem nos limites dos provedores.
6. Invalida o cache de caminhos da biblioteca para que a página da Biblioteca e o player vejam o resultado sem esperar o curto TTL de varredura habitual.

A sincronização roda **em segundo plano**. Você pode sair das Configurações; voltar enquanto ela ainda trabalha mostra que continua sincronizando. Quando termina, as Configurações mostram o **último log de sincronização** (importados / duplicados / erros, mais observações sobre letras/capas).

Execute **Sincronizar pastas** de novo depois de colocar mais arquivos nessas pastas. Salvar a lista de pastas sem sincronizar também as inclui na próxima varredura da biblioteca (cerca de um minuto, ou no próximo download/exclusão).

Remover uma pasta da lista **desmapeia** a pasta: aquelas faixas saem da Biblioteca e do player, e os extras criados pelo Downtify (arquivos auxiliares `.lrc`, capas em cache) são excluídos. Os arquivos de áudio em disco ficam onde estão.

Pastas que não existem ou não são legíveis são informadas após a sincronização; as demais continuam sendo varridas.

## Caminhos na biblioteca

Os arquivos de pastas extras usam um caminho virtual `ext/<id>/…` (o id é um hash do caminho da pasta, então a lista pode ser reordenada). O player e `GET /media/…` usam esse caminho, como `slskd/…` para arquivos do Soulseek deixados no lugar.

Uma pasta que já fica **dentro** de `/downloads` (ou da pasta de origem do slskd) é ignorada aqui — essa árvore já é a biblioteca.

## API

| Método | Caminho                       | Descrição                                                                        |
| ------ | ----------------------------- | -------------------------------------------------------------------------------- |
| `POST` | `/api/library/external/sync`  | Inicia uma varredura em segundo plano. Um corpo opcional `{folders: ["/path", …]}` é salvo antes. |
| `GET`  | `/api/library/external/sync`  | Tarefa em andamento, ou o último log concluído.                                  |
| `POST` | `/api/library/external/unmap` | Remove uma pasta da biblioteca sem excluir o áudio.                              |

Veja a [referência da API](../api-reference.md#post-apilibraryexternalsync) para o formato da resposta.

## Pasta principal da biblioteca

Escolha **Configurações → Biblioteca → Primary library folder** para preferir uma das
pastas externas registradas. O padrão preserva o comportamento existente.
Artista, título completo (incluindo a versão) e álbum correspondentes são exigidos;
metadados desconhecidos não escondem outro arquivo. Uma origem selecionada pode representar
uma gravação cuja outra cópia inclui introduções ou finais de clipe.

Isso é uma preferência de listagem, não uma migração. Arquivos de origem, caminhos de playlists
armazenados, propriedade, curtidas e regras de visibilidade não são regravados nem excluídos.
Os selos de playlist são combinados no representante exibido; playlists salvas explicitamente
ainda tocam seus caminhos originais. Álbuns e versões diferentes na pasta escolhida
continuam separados. Uma pasta vazia ou indisponível recorre ao restante da biblioteca.
Removê-la redefine a preferência.
