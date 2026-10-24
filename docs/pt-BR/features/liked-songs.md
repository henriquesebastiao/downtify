---
icon: lucide/heart
---

# Músicas curtidas

Toque no coração de uma música para curti-la. Assim que uma música é curtida, o Downtify mantém uma playlist **Músicas curtidas** com todas as que você curtiu, deixando seus favoritos a um clique — no Downtify e em qualquer servidor de mídia apontado para a sua biblioteca.

Não há nada para ativar.

Os corações pertencem a quem os tocou: em um servidor com várias contas, cada pessoa tem suas próprias músicas curtidas (veja [Usuários e login](users.md#your-library)). O arquivo da playlist em disco guarda os corações dos administradores; as curtidas de todos os outros ficam no banco de dados da biblioteca e funcionam do mesmo jeito nos apps.


## Curtindo uma música

O coração fica ao lado de toda música da sua biblioteca — downloads e faixas de [pastas de música existentes](external-library.md):

- nas listas de faixas — Biblioteca, álbuns, artistas e playlists;
- na [barra do player](player.md#player-bar) (em telas a partir de 640px de largura);
- em [Tocando agora](player.md#now-playing), ao lado do título da música.

Toque para curtir e toque de novo para desfazer. Ele fica verde e a mudança vai para o servidor na hora, então um coração tocado no celular já está no desktop também — abas e dispositivos abertos acompanham sozinhos.

Só músicas da sua biblioteca podem ser curtidas. Um resultado de busca que você ainda não baixou não tem coração; baixe-o primeiro.

## A playlist

A primeira curtida cria a playlist, e um aviso curto oferece abri-la. Ela aparece como qualquer outra playlist — na barra lateral, na página Início e em **Biblioteca → Playlists** —, mas sempre em **primeiro lugar**, com um coração no lugar da capa. Suas músicas ficam ordenadas com a curtida mais recente no topo.

Desfazer a última curtida remove a playlist de novo; não sobra uma **Músicas curtidas** vazia por aí.

O título segue o seu [idioma](internationalization.md). Em disco, a playlist é um [arquivo M3U](m3u-export.md) simples com nome fixo:

```
<downloads>/Playlists/Downtify Liked Songs.m3u
```

É por isso que Jellyfin, Navidrome, Plex e companhia também a mostram: eles leem o mesmo arquivo. O nome é reservado de propósito. Playlists do Spotify chamadas *Liked Songs* são comuns, e uma playlist baixada com esse nome acabaria escrevendo no mesmo arquivo.

## Removendo todas as curtidas

Abra a playlist, depois **⋯ → Remover todas as curtidas** e confirme. Todos os corações são apagados e a playlist some.

::: info Suas músicas ficam
Remover curtidas nunca apaga áudio. Apenas os corações e a playlist são removidos — os arquivos continuam na sua biblioteca. Isso é diferente de excluir uma playlist baixada, que exclui as músicas dela; **Músicas curtidas** nunca é tratada assim. Pedir para excluí-la (no app ou pela [API](../api-reference.md#delete-apilibraryplaylist)) apenas limpa as curtidas.
:::

## Mantendo as curtidas em sincronia com os arquivos

Uma curtida acompanha o arquivo ao qual foi dada:

| O que acontece com o arquivo | O que acontece com a curtida |
|--------------------------|--------------------------|
| Você exclui a música no Downtify | A curtida vai junto, e a playlist é reescrita |
| Você o move e executa [Corrigir caminhos da biblioteca](library-catalog.md#fix-library-paths) | A curtida acompanha o arquivo até o novo lugar |
| Ele some fora do Downtify (disco desmontado, exclusão manual) | A curtida é mantida, mas a música fica fora da playlist até voltar |

Manter a curtida de um arquivo ausente significa que um disco desconectado não te custa os corações. Se você apagou arquivos à mão e quer as curtidas apagadas também, use **Remover todas as curtidas** ou descurta as músicas antes de apagá-las.

## Bom saber

- As curtidas ficam no banco de dados da biblioteca (`downtify_library.db`, no seu volume `/data`), não nos arquivos de áudio. Nada é escrito nas tags da música.
- A playlist não é criada no [Navidrome](slskd-navidrome.md) pelo Downtify. É um arquivo M3U simples, então o que um servidor de mídia faz com ele depende de como esse servidor lê arquivos M3U.
- O [arquivo da playlist](m3u-export.md) é escrito mesmo com *Gravar playlists M3U* desativado nas configurações de download: a playlist é o objetivo do recurso.

## API

`GET /api/likes`, `PUT /api/likes` e `POST /api/likes/clear`, além de um sinalizador `liked` em [`GET /playlists`](../api-reference.md#get-playlists). Veja a [referência da API](../api-reference.md#likes).
