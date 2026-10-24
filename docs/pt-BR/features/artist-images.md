---
icon: lucide/image
---

# Foto, banner e biografia do artista

O Downtify pode mostrar uma foto de perfil de verdade, um banner e uma biografia para cada artista da sua Biblioteca, em vez de uma inicial gerada e nenhum texto. Isso se preenche sozinho na primeira vez que você abre a página de um artista novo, ou assim que uma faixa dele termina de baixar; depois disso, você escolhe outra foto/banner, busca de novo ou escreve a sua própria biografia e preenche os links sociais à mão.

A opção de edição está sempre disponível na página de cada artista da Biblioteca, sem precisar ligar nenhuma configuração antes.

::: info Sobre "Obter fotos de artista automaticamente" / "Obter banners de artista automaticamente" em Configurações
**Configurações → Downloads e arquivos → Obter fotos de artista automaticamente / Obter banners de artista automaticamente** decidem se o Downtify pode salvar sozinho a foto/banner de um artista — isso acontece na primeira vez que você abre a página dele e quando uma faixa dele termina de baixar (veja [A primeira vez que você abre um artista novo](#the-first-time-you-open-a-new-artist) e [Quando um download termina](#when-a-download-finishes)). As fotos vêm ligadas por padrão, os banners desligados. Elas nunca limitam a janela de edição: você sempre pode escolher uma foto ou banner à mão, seja qual for o valor delas.
:::

## A janela de edição

**Quando um artista tem um banner definido, a foto redonda dele fica oculta no cabeçalho da página** — o banner sozinho costuma bastar, e mostrar os dois ficava poluído. A foto não sumiu, porém: ainda está lá para editar, a uma aba de distância.

Na página de um artista na Biblioteca (`/library/artist?name=…`), passe o mouse sobre a foto redonda (quando exibida) para ver o botão **Editar foto**, ou sobre a área do banner para ver o botão **Editar artista** — ambos abrem a mesma janela: a foto atual do artista no topo e, abaixo dela, um menu com quatro abas. Ela abre em **Perfil** ou **Banner**, conforme o botão em que você clicou (por padrão **Banner**, já que a foto nem sempre está visível para clicar).

- **Perfil** / **Banner** — escolha uma imagem do mesmo jeito em qualquer um:
  - **Buscar pelo nome** — procura no YouTube Music e no Deezer uma foto do artista que corresponda (artistas do Deezer que só têm a imagem genérica de placeholder ficam de fora). Digite outra coisa para buscar outro nome, ou um link direto de imagem `http(s)://` para usá-lo como candidato avulso.
  - **Enviar do seu computador** — qualquer arquivo de imagem.
  - **Remover foto / Remover banner** — só aparece depois que a imagem da aba ativa está salva; pede confirmação e depois exclui o arquivo auxiliar (sidecar).

  Cada cartão de resultado de busca traz um selo de onde veio. Escolher um baixa e salva na hora. O cartão cuja imagem é a que está salva no momento recebe uma borda verde e um visto, nas abas Perfil e Banner separadamente — assim você vê de relance qual dos candidatos está usando. Uma foto que você enviou, ou uma salva antes de o Downtify começar a lembrar disso, não tem cartão para marcar.
- **Bio** — uma caixa de texto simples com a biografia salva no momento (em branco se não houver), para você escrevê-la ou editá-la. Salvar sobrescreve o texto atual diretamente. Um botão ⚡ **Buscar bio no Streams** acima da caixa pode preenchê-la com dados do Apple Music/Deezer em vez de digitar à mão — veja [Buscando uma biografia automaticamente](#fetching-a-bio-automatically) abaixo.
- **Redes sociais** — links de Twitter/X, Instagram, Facebook, YouTube e site, editáveis diretamente. Salvar sempre substitui os cinco campos pelo que está no formulário, mesmo um campo deixado em branco. Buscar uma biografia nunca mexe em um link que você preencheu: os links sociais do Deezer só preenchem campos ainda vazios (o Deezer não conhece todas as redes, então complete o resto à mão e ele continua assim).

## A primeira vez que você abre um artista novo

Abrir a página de um artista da Biblioteca preenche o perfil dele automaticamente, mas só se nada tiver sido salvo para ele ainda — toda visita depois da primeira é um não-faz-nada rápido, então isso nunca se repete nem deixa nada mais lento depois de rodar.

- **Foto e banner** — do Spotify (veja [Spotify](#spotify) abaixo), recorrendo a uma correspondência exata de nome no YouTube Music quando o Spotify não tem nada. Só quando você ligou **Obter fotos de artista automaticamente** e/ou **Obter banners de artista automaticamente** em Configurações (os dois vêm desligados por padrão, e cada um é independente); a janela de edição sempre pode definir qualquer um à mão.
- **Bio, origem, ano de formação, gênero, indicação de grupo, cor do banner, links sociais, artistas relacionados e ids de plataformas** — buscados no Apple Music e no Deezer como descrito em [Buscando uma biografia automaticamente](#fetching-a-bio-automatically) abaixo.

Se o Apple Music ou o Deezer **falha** enquanto isso roda (inacessível, ou acima do limite de requisições), nada é salvo — nem a bio, nem uma foto — e a página simplesmente não mostra perfil ainda, então a próxima visita tenta de novo. Só um serviço respondendo que não conhece o artista conta como resposta: o perfil é então feito com o que o outro tinha. A parte do Spotify (os artistas relacionados) nunca impede que um perfil seja feito.

## Quando um download termina

O mesmo preenchimento roda em segundo plano quando uma faixa de um artista termina de baixar — seja você que a iniciou no app ou uma varredura do [Monitor de playlists](playlist-monitor.md) — se esse artista ainda não tem perfil, então os artistas que você baixa ficam prontos antes mesmo de você abrir a página deles. Isso nunca deixa o download mais lento: o artista entra na fila e é preenchido alguns segundos depois, dois artistas por vez, e um que já está na fila não entra de novo por mais faixas dele que cheguem (uma playlist de cinquenta músicas de um artista o preenche uma vez). Músicas que já estavam na sua biblioteca não são baixadas de novo e não disparam nada.

- **Qual artista** — aquele sob o qual o arquivo é guardado: o artista do álbum, senão o primeiro artista creditado. `Various Artists` é ignorado.
- **Idioma** — a bio e o gênero vêm no idioma da interface web, que a página mantém no servidor (veja [Internacionalização](internationalization.md)); até uma página informá-lo, em inglês.
- **Foto e banner** — só como **Obter fotos de artista automaticamente** / **Obter banners de artista automaticamente** permitem, lidos naquele momento, então mudar uma configuração vale já para a próxima faixa.
- **Top songs** — não são feitas assim; esperam a página do artista (veja [Top songs](top-songs.md)).

Se nada puder ser encontrado em lugar nenhum para um artista, isso ainda assim só roda uma vez — não tenta de novo a cada visita seguinte. Use a janela de edição para escolher uma foto/banner à mão ou tentar o botão de buscar de novo a qualquer momento depois.

## A aba Links

Um artista com pelo menos um link salvo ganha uma aba **Links**, logo antes de **Bio** (que continua sendo a última aba), com um contador de quantos. Ela os lista como cartões, em qualquer tela e quer o artista tenha banner ou não: **Plataformas de streaming** primeiro, depois **Redes sociais**. Cada cartão mostra o nome e o endereço do site e o abre em uma nova aba. Só o que está realmente salvo é listado, e um artista sem links não tem aba Links (`?tab=links` para ele abre a primeira aba).

- **Plataformas de streaming** — Spotify, YouTube Music, Deezer e Apple Music, montadas a partir do `platforms_id` do perfil: cada id salvo vira um link (por exemplo, um id do Deezer salvo vira um link para a página do artista no Deezer). Os ids são todos resolvidos automaticamente na primeira vez que uma bio é buscada, por correspondência exata de nome em cada plataforma (o do Spotify vem de uma das faixas do próprio artista no Spotify quando há, o que não pode escolher um homônimo). Você também pode acrescentar ou corrigir um à mão no JSON do perfil do artista (veja abaixo).
- **Redes sociais** — Twitter/X, Instagram, Facebook, YouTube e site: um cartão por campo não vazio da aba Redes sociais acima. Só endereços web são abertos: um link digitado sem `https://` recebe, e qualquer coisa com outro tipo de endereço (um `javascript:`, por exemplo) é ignorada.

## Spotify

O Spotify nunca aparece como fonte de busca de texto livre, mas tanto o seletor quanto o preenchimento automático da primeira visita (veja acima) ainda encontram o artista lá. Eles primeiro conferem algumas faixas do próprio artista já baixadas: se uma foi baixada do Spotify, o Downtify já conhece o id dessa faixa no Spotify e resolve a imagem diretamente — o caminho mais confiável, já que não pode cair em outro artista com o mesmo nome. Quando nenhuma faixa veio do Spotify (digamos, foram baixadas do YouTube), o artista é procurado por nome exato (sem diferenciar maiúsculas — uma correspondência aproximada nunca é usada). No seletor, esse candidato aparece primeiro, rotulado **Spotify**.

A busca por nome usa a caixa de pesquisa do próprio player web do Spotify, então depende de um identificador interno que o Spotify pode mudar; se isso acontecer, o Downtify recorre ao YouTube Music para a foto/banner e deixa o id do Spotify vazio, em vez de falhar.

Foto e banner são imagens realmente diferentes no Spotify, resolvidas de modos diferentes: a foto quadrada vem da página de embed pública do artista, enquanto o banner largo vem dos dados da própria página do artista no Spotify (que o embed nem expõe). Nem todo artista tem um banner definido — quando não tem, nenhum candidato do Spotify é oferecido ao seletor de banner, em vez de recorrer à foto quadrada.

Um artista sem faixas vindas do Spotify ainda simplesmente não ganha candidato do Spotify — pesquise no YouTube Music/Deezer, cole um link ou envie uma imagem.

## Buscando uma biografia automaticamente

Abaixo do cabeçalho, a página do artista mostra uma biografia curta, somente leitura — vazia até que uma seja salva. Para preenchê-la, abra a aba **Bio** da janela de edição e clique em **Buscar no Apple Music** ou **Buscar no Deezer** acima da caixa de texto (veja [Escolhendo a fonte](#choosing-the-source)), o que carrega a bio desse serviço na caixa para você revisar e salvar. O preenchimento automático da primeira visita, que salva por conta própria, procura o artista no Apple Music por correspondência exata de nome (usando a mesma busca por nome do app Música da própria Apple) e busca a bio, a origem, o ano de formação, o gênero, a indicação de grupo e a cor de destaque do banner — o texto (bio e gênero) no idioma atual da sua interface — e salva o resultado. O gênero (o Apple Music dá um por artista, por exemplo "Hard rock") aparece como uma pequena pílula no topo da aba Bio da página do artista, ao lado da origem e do ano de formação. O Apple Music diz se o artista é um grupo: para um grupo essa data é lida como "Formado em 1995", e para um artista solo — cuja data costuma ser de nascimento — "Nascido em 27 de setembro de 1984" (traduzido em todos os idiomas da interface; um artista cuja indicação de grupo não é conhecida fica em "Formado em"). A data em si é mostrada do jeito que o Apple Music a deu, então mantém o idioma da busca. Se o Apple Music não tem correspondência exata, ou tem mas sem texto de bio no seu idioma, o Deezer é tentado em seguida como fonte secundária de bio — ele também traz links sociais e nomes de artistas relacionados de "fãs também curtem" (os artistas relacionados são salvos no arquivo de perfil do artista mas ainda não aparecem em lugar nenhum, reservados para uma adição futura), preenchendo também a aba Redes sociais. Só se nenhuma das duas fontes tem qualquer coisa você vê um erro em vez de uma bio adivinhada/errada.

As biografias editoriais do próprio Apple Music não são escritas para todo artista em todo idioma — quando falta um idioma para um artista específico, a bio do Deezer (se tiver) é usada no lugar, enquanto origem/ano de formação/indicação de grupo ainda vêm do Apple Music, já que esses fatos não são texto traduzido (o gênero é sempre só do Apple Music, então fica vazio quando a Apple não tem correspondência). Alguns idiomas (o búlgaro, no momento em que isto foi escrito) não são oferecidos pelo Apple Music e sempre recorrem à bio no idioma padrão dele.

Uma bio é guardada no JSON do artista como texto simples — sem tags HTML e sem caracteres de marcador: uma linha em branco separa os parágrafos, e cada marcador `•` de uma bio do Apple Music (que a Apple separa com uma única quebra de linha) vira um parágrafo próprio. As bios em HTML do Deezer são achatadas do mesmo jeito (cada parágrafo vira um separado por linha em branco, qualquer outra tag é descartada). A página do artista mostra cada parágrafo à parte e mantém as quebras de linha simples dentro dele, e a caixa de texto da aba Bio edita exatamente esse texto.

Buscar de novo assim só roda quando você clica no botão — ele não sobrescreve nada por conta própria depois do preenchimento automático da primeira visita descrito acima. Só na primeira vez (seja o preenchimento automático ou um clique manual) é preciso buscar por nome: os ids de artista do Apple Music e do Deezer resolvidos ficam em cache no arquivo de perfil do artista depois, então buscar de novo apenas relê os mesmos artistas diretamente.

Para limpar uma bio salva, abra a aba Bio, esvazie a caixa de texto e Salve — origem, ano de formação, gênero, indicação de grupo, links sociais, artistas relacionados e os ids de plataformas em cache ficam intocados.

## Escolhendo a fonte

A aba Bio tem dois links acima da caixa de texto, para você escolher qual biografia lê melhor:

- **Buscar no Apple Music** — carrega a bio editorial do Apple Music na caixa de texto. Se o Apple Music não tem nenhuma para este artista no seu idioma, você recebe um erro em vez de um substituto.
- **Buscar no Deezer** — carrega a bio do Deezer, mesmo quando o Apple Music tem uma. Se o Deezer não tem nenhuma, você recebe um erro.

Clicar em um link **só preenche a caixa de texto** — nada é salvo até você pressionar **Salvar**, então você pode lê-la, editá-la ou tentar o outro serviço primeiro, e fechar a janela sem salvar deixa a bio atual como estava. Só o texto da bio é carregado: a origem, o ano de formação, o gênero, os links sociais, os artistas relacionados e os ids de plataformas não são tocados por esses links (o preenchimento automático da primeira visita é que os preenche). O preenchimento automático não pergunta qual serviço: usa a bio do Apple Music e recorre à do Deezer só quando o Apple Music não tem nenhuma.

## Para onde vão os arquivos

```
<downloads>/.metadata/ArtistImage/<Artist>.jpg
<downloads>/.metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/.metadata/ArtistData/<Artist>.json
<downloads>/.metadata/ArtistTopSongs/<Artist>.topsongs.json
```

Um arquivo por artista, com o nome dele (higienizado do mesmo jeito que os nomes de arquivo das faixas) — sem registro em banco de dados, então a presença do arquivo no disco é o que a página do artista confere. Salvar uma foto/banner nova sobrescreve a anterior (a interface web impede que a cópia antiga continue aparecendo: a URL de cada imagem salva carrega a data de modificação do arquivo, então uma foto substituída é buscada de novo enquanto uma intocada continua em cache), e `ArtistData/<Artist>.json` guarda os dados de bio/redes sociais/artistas relacionados/ids de plataformas descritos acima, além de, em `current_cover` e `current_cover_banner`, qual imagem é a foto/banner atual: o caminho da URL de onde foi baixada (sem o host e a query, para que a mesma imagem de outro endereço de CDN ainda corresponda), ou `upload` para uma que você enviou. É com isso que a janela de edição compara cada candidato para marcar o que está em uso. São arquivos comuns na sua pasta de downloads, então serviços como o Navidrome podem lê-los diretamente se você apontá-los para o mesmo local.

Os nomes de artistas são comparados do jeito que o disco os guarda: o Downtify arquiva `AC/DC` como `ACDC`, porque um nome de arquivo não pode conter `/`, e uma faixa sem tag de artista pega o artista desse nome de arquivo — então o mesmo artista pode aparecer como `AC/DC` ou `ACDC`. Toda busca por nome (Spotify, Deezer, YouTube Music e Apple Music) ignora maiúsculas e os caracteres que um nome de arquivo não suporta, então as duas grafias encontram o mesmo artista, e ambas compartilham os mesmos arquivos acima. Um nome que difere em qualquer outra coisa — `AC/DC Tribute`, digamos — continua sendo outro artista e nunca corresponde.

O `platforms_id` reconhece as chaves `spotify`, `youtubemusic`, `deezer` e `applemusic`, todas resolvidas automaticamente — a do Spotify a partir de uma das faixas do próprio artista no Spotify ou, na falta, por nome exato; as outras por nome exato. Buscar a bio também preenche um id do Spotify que falta, então um artista aberto antes de isso existir ganha o ícone do Spotify depois de uma busca. Um id já salvo nunca é substituído, e você ainda pode editar o arquivo JSON diretamente para definir um à mão.

## Fora do escopo

Escolher uma foto/banner aqui nunca toca o pipeline de download — não tem efeito sobre o que é incorporado nas tags dos próprios arquivos de áudio, e baixar uma faixa nunca busca uma imagem de artista automaticamente.

A aba *Relacionados* mostra uma foto também para artistas que você não tem, e o mesmo fazem a grade de *Artistas* da Biblioteca, a página do próprio artista, a aba *Artistas* do Monitor (o artista que você está monitorando, na lista e na janela de edição dele) e os artistas no [Descobrir](discover.md) e no [Finder](finder.md) — onde a página já tem a imagem do artista no Deezer, então não é preciso buscar pelo nome, e uma foto que você salvou para o artista aparece no lugar — para todo artista para o qual você não escolheu uma foto (a Biblioteca e a página do próprio artista usam uma das capas de faixa do artista quando o Deezer não tem nenhuma; o Monitor não tem faixa, então mostra as iniciais) - só uma de verdade: um artista para o qual o Deezer não tem foto (ele serve um placeholder genérico) ganha a inicial de sempre - mas é só para exibição: o servidor repassa a imagem do Deezer ao seu navegador (que a guarda em cache por três horas) sem salvá-la, e ela nunca vira a foto ou o banner de um artista. Só respostas reais são mantidas: se o Deezer não puder ser alcançado ou você estiver acima do limite de requisições naquele momento, o bloco mostra a inicial (ou a capa da faixa) por enquanto e nada é lembrado, então a foto aparece na próxima vez que você abrir a página. As fotos só são gravadas em disco para artistas para os quais você mesmo definiu uma, ou cuja foto/banner foi salva na primeira visita como descrito acima (quando as Configurações permitem). Veja [`GET /api/artists/photo-proxy`](../api-reference.md#get-apiartistsphoto-proxy).
