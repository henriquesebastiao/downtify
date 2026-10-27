---
icon: lucide/smartphone
---

# Apps para celular

O Downtify pode atender apps no seu celular: eles navegam pela biblioteca e a tocam em streaming direto do seu servidor, e guardam músicas no celular para ouvir offline. Tudo o que um app precisa é configurado em **Configurações → Apps**: o pareamento dos celulares e o nome do servidor. Quem pode usar o servidor é definido pelas contas em [Usuários e login](users.md).

::: warning O app ainda está em desenvolvimento
**Configurações → Apps** está marcado como *Experimental*. O lado do servidor descrito nesta página está pronto e funcionando, mas **nenhuma versão do app Android foi publicada ainda**, então por enquanto não há nada para instalar, e detalhes do pareamento e do streaming ainda podem mudar entre versões do Downtify.

O app é construído de forma aberta em [henriquesebastiao/downtify-android](https://github.com/henriquesebastiao/downtify-android). Qualquer outro app pode ser feito sobre a mesma API — veja o [contrato do cliente móvel](../mobile-client-contract.md).
:::

## Entrando pelo app

Digite o endereço do servidor (ou escolha-o em **Encontrados nesta rede**) e entre com **o mesmo usuário e senha** da página web. O celular aparece em **Apps pareados**, exatamente como se você o tivesse pareado com um código abaixo: ele toca como você, guarda uma chave própria (a senha não fica guardada no celular) e **Desparear** o bloqueia.

Senhas erradas têm limite de tentativas junto com o login da página web. Enquanto as contas estão desligadas (`DOWNTIFY_DISABLE_AUTH`), não há com o que entrar: pareie com um código.

## Pareando um celular

Parear não pede senha no celular: prático quando a página web já está aberta, ou num celular em que você prefere não digitar sua senha.

1. Abra **Configurações → Apps** e pressione **Parear um celular**.
2. No app, escolha **Escanear o código** e aponte a câmera para o QR code — ou digite o código de 8 caracteres exibido abaixo dele (`K7QM-2XPD`; maiúsculas e hifens não importam).
3. A janela confirma quando o celular está pareado, e ele aparece em **Apps pareados**.

O celular é pareado à **sua conta**: ele toca como você e aparece na sua atividade. Qualquer pessoa com uma conta pode parear os próprios celulares.

Um código funciona **uma vez**, por **cinco minutos**, e tentar códigos errados tem limite de tentativas. O celular recebe uma chave própria que ele guarda; o servidor só armazena um hash dela.

**Apps pareados** lista os seus celulares (um admin vê os de todos, com o dono de cada um) com a plataforma, quando foi visto pela última vez e de qual endereço. **Desparear** bloqueia um celular na hora — a próxima requisição dele falha, uma conexão aberta é encerrada e os links que ele compartilhou (veja [Transmissão (cast)](#casting)) deixam de funcionar. Para usá-lo de novo, pareie-o outra vez.

## O que um app pareado pode fazer

Apps pareados podem navegar, tocar, curtir, guardar músicas offline e pedir ao servidor que baixe músicas — mas não alterar configurações e credenciais nem excluir arquivos; isso exige a página web, conectado como admin.

**Configurações → Apps → Sair de todos os lugares** desparea todos os seus apps e desconecta você de todos os navegadores, inclusive este. Login, contas e senha esquecida estão em [Usuários e login](users.md).

## Encontrando o servidor na sua rede

O servidor se anuncia na rede local (mDNS / Bonjour, como `_downtify._tcp`), então um app o lista em **Encontrados nesta rede** — nome, endereço e versão — sem precisar digitar nada. O nome é o definido em **Configurações → Apps → Nome do servidor** (o hostname da máquina até você mudá-lo).

::: info A rede padrão do Docker esconde o anúncio
Na rede *bridge* padrão do Docker, o anúncio fica dentro do Docker e os celulares não o veem. Ou rode o contêiner com `network_mode: host` (veja [Docker Compose](../getting-started/docker-compose.md#finding-the-server-from-the-apps)), ou digite o endereço do servidor no app — todo o resto funciona igual.
:::

Defina `DOWNTIFY_DISCOVERY=false` para parar de anunciar.

## Qualidade do streaming

Os apps tocam os arquivos como estão (**Original**) ou pedem ao servidor uma cópia menor: Opus, AAC ou MP3 a 96–320 kbps — útil em dados móveis. O servidor faz essa cópia com o ffmpeg na primeira vez que uma música é tocada assim (alguns segundos para uma música comum) e a mantém, então avançar e voltar funciona como em qualquer arquivo e a próxima reprodução é instantânea.

- Um arquivo que já é pequeno o bastante (um arquivo com perdas em bitrate igual ou menor que o pedido) é enviado como está, nunca recodificado.
- As cópias ficam em `/data/transcode_cache`, no máximo 2 GB por padrão; as tocadas há mais tempo saem primeiro. No máximo duas são feitas ao mesmo tempo. Os dois limites são [variáveis de ambiente](../getting-started/environment-variables.md#mobile-apps-and-sign-in).
- Se o celular desiste enquanto uma cópia está sendo feita, o servidor para de fazê-la.

## Transmissão (cast)

Os apps podem enviar uma música para um Chromecast ou outro player que busca o áudio por conta própria. O app recebe do servidor um link que vale para aquela música por um tempo limitado (uma hora por padrão) e só enquanto o celular continuar pareado; nenhuma chave do celular vai dentro dele.

## Atrás de um proxy reverso

Se o Downtify fica atrás de nginx, Caddy, Traefik ou similar (para HTTPS, ou para alcançá-lo de fora):

- **Deixe o WebSocket passar.** `/api/ws` precisa que os cabeçalhos `Upgrade`/`Connection` sejam repassados (Caddy e Traefik fazem isso por padrão; o nginx precisa de `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`).
- **Repasse as requisições Range** sem alteração e não coloque respostas de áudio em buffer (nginx: `proxy_buffering off;` para `/api/v1/` e `/downloads/`), ou avançar e arquivos grandes sofrem.
- **Diga ao Downtify em qual proxy confiar.** Defina `DOWNTIFY_TRUSTED_PROXIES` com o endereço do proxy (por exemplo `172.18.0.0/16`). Só então o Downtify usa `X-Forwarded-For` para o endereço do cliente (limites de tentativas, "visto pela última vez" em Apps pareados) e `X-Forwarded-Proto`/`X-Forwarded-Host` para marcar o cookie de login como seguro e verificar de onde vêm as requisições. Sem isso, esses cabeçalhos são ignorados — qualquer um poderia enviá-los.
- **Use HTTPS** quando o servidor for acessível de fora: a senha e as chaves dos apps viajam em cada requisição.

## Para desenvolvedores de apps

Todo o fluxo que um app segue — descoberta, pareamento, sincronização da biblioteca, streaming, relato de reproduções — está no [contrato do cliente móvel](../mobile-client-contract.md), e cada endpoint está na [referência da API](../api-reference.md#server-and-sign-in).
