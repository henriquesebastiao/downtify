---
icon: lucide/users
---

# Usuários e login

Todo mundo que usa o Downtify entra com um **usuário e senha**, e cada pessoa pode ter a própria conta. Um admin gerencia as contas em **Configurações → Usuários** e vê o que cada um faz em **Configurações → Atividade**.

## Entrando pela primeira vez

Um servidor novo tem uma conta:

| Usuário | Senha |
|----------|----------|
| `admin` | `downtify` |

Entre com ela e **mude a senha** em **Configurações → Geral → Conta**: quem conhece o Downtify conhece a senha padrão. Até você mudá-la, o Downtify lembra você depois do login e mostra um aviso em Configurações.

::: warning Mude a senha padrão antes de expor o servidor
A senha padrão não protege nada. Mude-a antes de tornar o Downtify acessível de fora da sua rede doméstica — e use HTTPS lá (veja [Atrás de um proxy reverso](mobile-apps.md#behind-a-reverse-proxy)).
:::

### Atualizando de uma versão antiga

Um servidor que rodava uma versão sem contas ganha a mesma conta `admin`, e a página de login avisa isso uma vez — até um admin entrar — com o usuário e a senha a usar:

- Se você tinha definido uma senha na antiga opção **Exigir login**, essa senha continua valendo para o `admin`.
- Senão, é `downtify`.

Os navegadores conectados antes da atualização entram de novo. Os celulares pareados antes dela continuam pareados e agora pertencem ao `admin`.

## Admins e usuários

| | Admin | Usuário |
|---|---|---|
| Ouvir, pesquisar, baixar, curtir, Descobrir, Paradas de sucesso, Finder, podcasts | ✓ | ✓ |
| Parear apps de celular (à própria conta) | ✓ | ✓ |
| Configurações → Geral (a própria conta e preferências), Apps, Sobre | ✓ | ✓ |
| Todas as outras configurações (fontes, arquivos, tags, Navidrome, biblioteca, servidor), renomear o servidor | ✓ | |
| [Compartilhar as próprias playlists](#sharing-playlists) (só visualização), seguir as públicas, salvar cópias | ✓ | ✓ (quando o admin permite) |
| Excluir arquivos e playlists (um usuário só [o que baixou](#deleting-songs) e as próprias playlists), gerenciar os próprios monitoramentos de playlists e assinaturas de podcasts, substituir o áudio de uma faixa, editar fotos de artistas | ✓ | ✓ (só os próprios) |
| [Ocultar músicas, álbuns e artistas dos usuários](#hiding-from-users) | ✓ | |
| Gerenciar usuários, ver o registro de atividade | ✓ | |

Um usuário que tenta algo que exige admin recebe uma mensagem dizendo isso.

## Sua biblioteca

A biblioteca é compartilhada: cada conta vê todas as músicas que qualquer um baixou — na Biblioteca, nos resultados de pesquisa marcados como baixados e num celular pareado. Os arquivos nunca são guardados duas vezes: quando duas pessoas baixam a mesma música, ela vai para o disco uma vez, com um dono para cada.

As curtidas, as playlists (baixadas e criadas na Biblioteca) e a fila de downloads continuam sendo suas, a menos que você seja admin — ou [compartilhe uma playlist](#sharing-playlists) para que outros a vejam. A audição é compartilhada — qualquer um pode tocar, ouvir uma prévia ou transmitir qualquer faixa, e adicionar qualquer coisa às próprias playlists. Pedir uma faixa que outra pessoa já está baixando entra no trabalho dela em vez de buscar duas vezes: uma linha na fila, um download e uma posse para cada — cada um que espera vê sua posição na fila.

Podcasts, monitoramentos de playlists e o histórico do Descobrir funcionam do mesmo jeito: cada conta assina os próprios programas, segue as próprias playlists e artistas e treina as próprias sugestões. Um admin vê as linhas de todas as contas. A audição em si continua compartilhada — qualquer um pode tocar, ouvir uma prévia ou transmitir qualquer faixa.

### Compartilhando playlists

Uma playlist é privada para o dono (e os admins) até que o dono a compartilhe, em **Compartilhar…** na página da playlist ou no menu **⋯** dela. A reprodução já é compartilhada entre as contas; isto é só sobre quem pode *ver* uma lista. Toda playlist pode ser compartilhada, exceto *Músicas curtidas*, inclusive as importadas.

| Visibilidade | Quem a vê |
|------------|-------------|
| **Privada** | Só o dono e os admins — o padrão |
| **Pessoas específicas** | Os usuários escolhidos pelo dono |
| **Pública** | Todos no servidor |

As playlists dos outros nunca se misturam com as suas. A aba **Playlists** da Biblioteca as lista em duas seções abaixo das suas, cada entrada com o nome do dono:

- **Compartilhadas comigo** — playlists direcionadas a você pelo nome, sempre exibidas. Uma recém-compartilhada tem a marca **Nova** até você abri-la.
- **Playlists públicas** — as públicas de todos, ordenadas por dono e nome, pesquisáveis com o filtro da aba, mostrando o dono, o número de músicas e se você a segue. A seção começa recolhida, e você pode ocultá-la por completo em **Configurações › Geral › Mostrar playlists públicas** (ligado por padrão; é seu, como o tema).

A barra lateral também mostra algumas das que foram compartilhadas com você e das playlists públicas que você segue.

**O que quem visualiza pode fazer:** tocar, embaralhar, adicionar à fila, baixar como ZIP (ou para um app de celular ou de computador), **Seguir** uma playlist pública para que ela continue nas suas listas — mesmo com *Mostrar playlists públicas* desligado — e acompanhar as mudanças do dono, e **Salvar uma cópia**: uma playlist privada e editável só dele, com as músicas que ele pode ver. Quem visualiza não pode editar, renomear, excluir, compartilhar nem desvincular a playlist de outra pessoa. O dono de uma playlist da biblioteca também pode tornar algumas das pessoas com quem a compartilha editoras dela, que adicionam e removem músicas — veja [Playlists colaborativas](collaborative-playlists.md).

**Descompartilhar:** quando o dono torna a playlist privada de novo, ou tira alguém da lista, ela sai das listas dessa pessoa na hora (seguida ou não); uma playlist que deixa de ser pública não é mais seguida. As cópias que as pessoas já salvaram ficam com elas. Renomear uma playlist compartilhada a mantém compartilhada; excluí-la leva o compartilhamento junto. As músicas que um admin [oculta dos usuários](#hiding-from-users) ficam de fora das faixas de uma playlist compartilhada para eles, como em todo lugar.

Um admin pode desligar tudo isso em **Configurações › Biblioteca › Permitir que usuários compartilhem playlists** (ligado por padrão). Enquanto está desligado, todo compartilhamento fica oculto e ninguém pode compartilhar nem seguir — os compartilhamentos voltam quando é ligado de novo.

Os apps pareados recebem as mesmas listas: [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) diz quem é o dono de cada uma e se é só visualização, e `playlists_changed` no WebSocket avisa para atualizar.

### Ocultando dos usuários

Os admins decidem o que as outras contas veem. Tudo é visível para todos até que um admin oculte algo: uma **música**, um **álbum** inteiro ou um **artista** inteiro. Itens ocultos saem da Biblioteca, das marcações "na biblioteca" da pesquisa, das listas de faixas das playlists e do que um celular pareado sincroniza — para os usuários, não para os admins.

- **Na Biblioteca**, abra o menu `…` de uma música, álbum ou artista e escolha **Ocultar dos usuários** (ou **Mostrar aos usuários** para desfazer). Na aba Faixas, selecione várias músicas e use **Ocultar dos usuários** na barra de seleção.
- Os admins continuam vendo tudo. O que está oculto carrega um pequeno olho riscado, e a dica dele diz por quê: oculto por conta própria, com o álbum ou com o artista.
- **Configurações › Usuários › Oculto dos usuários** lista cada artista, álbum e música oculta, com **Mostrar aos usuários** ao lado de cada um.
- Uma música oculta continua oculta quando é movida para outra pasta e quando [Melhorar biblioteca](library-upgrade.md) ou [Substituir áudio](replace-audio.md) reescrevem o arquivo dela. Excluir o arquivo esquece a regra.
- Uma regra de álbum corresponde ao artista e ao título do álbum, e uma regra de artista ao artista sob o qual a Biblioteca agrupa a música — os mesmos nomes que as abas Álbuns e Artistas da Biblioteca usam.

::: info Ocultar é sobre o que é listado
Controla o que as contas veem no app, não quem pode buscar um arquivo cujo endereço já conhece. Não use isso para proteger arquivos sensíveis.
:::

Ocultar e mostrar ficam registrados no [registro de atividade](#activity).

### Excluindo músicas

Excluir uma música a tira do disco para todos, então segue quem a baixou. Um admin pode excluir qualquer coisa. Um usuário pode excluir uma música que ele mesmo baixou; quando outra pessoa também baixou a mesma música, excluir só abre mão da posse dele e a música continua na biblioteca compartilhada. Uma música que ninguém baixou por uma conta (uma varredura do monitor de playlists, um download de antes das contas, uma [pasta extra](external-library.md)) só pode ser excluída por um admin. Excluir uma playlist sua nunca leva os arquivos de outra pessoa junto.

### Uso por conta

**Configurações › Usuários** lista, sob cada conta, o que ela tem: faixas e o tamanho delas, curtidas, playlists, downloads pedidos e tráfego nos dois sentidos (buscado na origem vs. servido aos clientes), com os totais de todos logo abaixo. "Faixas" conta as músicas que uma conta baixou, não o que ela pode ver.

## Sua conta e preferências

**Configurações → Geral** começa com a sua **Conta**: mude seu usuário ou senha, ou saia. Você também pode sair pela barra lateral (ou por **Mais** no celular).

O resto de **Geral** — tema, idioma, mostrar letras no player, álbuns nos resultados de pesquisa — é **seu**: acompanha a sua conta em todo navegador em que você entra e não muda nada para ninguém mais.

**Configurações → Apps** lista os celulares pareados à sua conta (um admin vê os de todos, com o dono). **Sair de todos os lugares** desparea seus apps e desconecta você de todos os navegadores.

## Gerenciando usuários

Em **Configurações → Usuários**, um admin pode:

- **Adicionar um usuário** — nome de usuário (3 a 32 letras, dígitos, `.`, `-` ou `_`), senha (mínimo de 8 caracteres) e papel.
- **Editar** um usuário — renomeá-lo, torná-lo admin ou usuário, ou dar uma senha nova (o que o desconecta dos navegadores; os apps dele continuam pareados).
- **Excluir** um usuário — os apps dele são desparelhados e os navegadores desconectados. Os arquivos dele ficam no disco (os admins ainda os veem); as curtidas, playlists, assinaturas de podcasts, monitoramentos, histórico de sugestões e contadores de tráfego vão com ele.
- **Desconectar todos** — todo app de todo usuário é desparelhado e todo navegador desconectado, o seu também.

Sempre há pelo menos um admin: o último não pode ser excluído nem virar usuário, e você não pode excluir a própria conta.

## Atividade

**Configurações → Atividade** (admins) mostra, como o painel do Jellyfin:

- **Tocando agora** — o que cada navegador e app está tocando, por quem, em que ponto da música está e se está pausado. Atualiza a cada poucos segundos.
- **Histórico** — logins (e os que falharam, com o endereço de onde vieram), saídas, músicas tocadas, downloads, curtidas, arquivos excluídos, músicas ocultadas ou mostradas aos usuários, apps pareados e desparelhados, contas adicionadas, alteradas ou excluídas, senhas e configurações alteradas. Filtre por usuário ou por tipo. As configurações salvas são listadas só pelo nome, nunca pelos valores. As entradas são mantidas por 90 dias.

Os apps também informam o que tocam — veja o [contrato do cliente móvel](../mobile-client-contract.md#8-report-plays).

## Desligando as contas

Um servidor que só você alcança — no seu computador, ou atrás de algo que já pede senha — pode nem precisar de contas. Defina `DOWNTIFY_DISABLE_AUTH=true` (veja [Variáveis de ambiente](../getting-started/environment-variables.md#mobile-apps-and-sign-in)):

```yaml
environment:
  - DOWNTIFY_DISABLE_AUTH=true
```

Então:

- Não há página de login: quem abrir o Downtify o usa como o primeiro admin (`admin` num servidor novo).
- Os botões de sair, **Configurações → Usuários**, a parte **Conta** de **Configurações → Geral** e **Sair de todos os lugares** em **Configurações → Apps** somem.
- Os celulares ainda podem ser pareados (a esse admin), e **Configurações → Atividade** ainda mostra o que toca onde.
- Tema, idioma e as outras preferências de **Geral** são mantidos como os desse admin.

::: warning Qualquer um que alcance o servidor pode fazer tudo
Com as contas desligadas, nada pergunta quem você é: todos na sua rede — ou na internet, se a porta estiver exposta — podem mudar configurações, excluir músicas e parear um celular. Não desligue as contas num servidor que outras pessoas alcançam.
:::

Defina como `false` (ou remova) e o login volta a ser exigido, com as contas, senhas e apps como estavam.

## Esqueceu a senha?

Rode isto no servidor — o `admin` recebe de volta a senha `downtify` (e é recriado como admin se foi renomeado ou excluído); as outras contas e os apps pareados ficam como estão:

```bash
docker exec downtify python main.py auth-reset
```

Fora do Docker, rode `python main.py auth-reset` (ou `uv run python main.py auth-reset`) na pasta do Downtify. Depois entre e mude a senha.

## Scripts e a API

Toda chamada da API agora exige credenciais (veja a [referência da API](../api-reference.md#server-and-sign-in)). Um script pode fazer login com `POST /api/auth/login` e guardar o cookie `downtify_session`, ou usar o token de um dispositivo pareado.
