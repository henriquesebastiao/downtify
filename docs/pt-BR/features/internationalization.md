---
icon: lucide/languages
---

# Internacionalização

O Downtify é traduzido em dois lugares independentes: o **app** (a interface) e esta **documentação**. O idioma padrão de ambos é o **inglês**, com outros nove idiomas incluídos de fábrica.

## Mudando o idioma

### O app

Vá em **Configurações → Idioma** e escolha o idioma de sua preferência. A escolha é salva no `localStorage` do navegador e aplicada na hora, sem recarregar a página. A página também informa o servidor (a entrada `ui_language` do `settings.json`, veja [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate)), a cada carregamento e sempre que você a muda, para que o trabalho que roda sem um navegador conheça o seu idioma - a biografia de um artista, buscada em segundo plano quando uma faixa dele termina de baixar, vem nele (veja [Quando um download termina](artist-images.md#when-a-download-finishes)). Não há nada a fazer do seu lado: se você escolheu um idioma antes de isso existir, ele é captado na próxima vez que você abrir o Downtify. Com vários navegadores em idiomas diferentes, vale o último que carregou ou mudou.

### A documentação

A documentação abre no idioma que o seu navegador prefere, quando há tradução para ele, e em inglês caso contrário. O **botão de globo** à direita da barra superior muda o idioma a qualquer momento e mantém você na mesma página (e seção). A sua escolha é lembrada no navegador e, a partir daí, vale mais que o idioma do navegador até você escolher outro.

Uma página ainda não traduzida mostra um aviso e o texto em inglês, então todo idioma sempre tem todas as páginas.

## Idiomas disponíveis

| Código | Idioma | App | Docs |
| ------- | ------------------ | --- | ---- |
| `en` | English (padrão) | ✓ | ✓ |
| `es` | Español | ✓ | ✓ |
| `pt-BR` | Português (Brasil) | ✓ | ✓ |
| `fr` | Français | ✓ | ✓ |
| `tr` | Türkçe | ✓ | ✓ |
| `el` | Ελληνικά | ✓ | ✓ |
| `hu` | Magyar | ✓ | ✓ |
| `bg` | Български | ✓ | ✓ |
| `de` | Deutsch | ✓ | ✓ |
| `ko` | 한국어 | ✓ | ✓ |

As páginas de referência feitas para desenvolvedores — a [referência da API](../api-reference.md), o [contrato do cliente móvel](../mobile-client-contract.md) e o changelog — ficam em inglês em todos os idiomas.

## Contribuindo com uma tradução

Você pode traduzir o app, a documentação ou ambos. São trabalhos separados, com arquivos separados, então um pull request pode conter um dos dois — ou um idioma pode ser adicionado a um deles primeiro e ao outro depois.

| Você traduz | Onde ficam os arquivos | Está pronto quando |
| ------------- | ------------------- | --------- |
| **Só o app** | `frontend/src/i18n/locales/<code>.js` | o idioma aparece em **Configurações → Idioma** |
| **Só a documentação** | `docs/.vitepress/locales/<code>.mjs` e as páginas Markdown em `docs/<code>/` | o idioma aparece no menu de globo da documentação |
| **Ambos** | todos os acima | ambos |

Um idioma não precisa existir no app para ser adicionado à documentação, nem o contrário.

## Traduzindo o app

Adicionar uma tradução ao app é um processo de três passos:

### 1. Copie o arquivo de idioma em inglês

Os arquivos de idioma ficam em `frontend/src/i18n/locales/`. Cada arquivo exporta um único objeto cujas chaves seguem a estrutura de `en.js`. Use uma [tag de idioma IETF](https://en.wikipedia.org/wiki/IETF_language_tag) como nome do arquivo.

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/it.js
```

### 2. Traduza os valores

Mantenha as chaves, os tokens de espaço reservado (por exemplo `{count}`, `{name}`, `{file}`) e a forma geral inalterados — só os textos do lado direito devem mudar. Defina `language.name` como o nome **nativo** do idioma (`"Français"`, `"Deutsch"`, …) — é o rótulo exibido no seletor de idioma.

### 3. Registre o idioma

Adicione um import e uma entrada em `AVAILABLE_LOCALES` em `frontend/src/i18n/index.js`:

```js
import it from './locales/it.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  // …
  { code: 'it', name: 'Italiano', messages: it }, // new
]
```

Recompile o frontend e o seu idioma aparecerá automaticamente em **Configurações → Idioma**:

```bash
cd frontend && npm run build
```

### Dicas para traduzir o app

- Chaves ausentes voltam ao inglês, então traduções parciais funcionam bem — envie um PR com o que tiver.
- Textos que dependem de um número são objetos com formas de plural, por exemplo `tracks: { one: '{count} track', other: '{count} tracks' }`. A forma é escolhida com o [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) do navegador para o seu idioma, então adicione as formas que o seu idioma usa (`zero`, `one`, `two`, `few`, `many`, `other`) — `other` é obrigatório. Os números são formatados para o idioma automaticamente.
- Tokens de espaço reservado como `{count}` ou `{file}` devem ficar inalterados; são substituídos em tempo de execução.
- Mantenha os textos concisos — a interface é bem justa e traduções muito longas podem quebrar de forma estranha.
- Depois de traduzir, rode `npm run dev` em `frontend/` e navegue por todas as páginas no seu idioma para achar o que transborda ou soa estranho no contexto.

## Traduzindo a documentação

O inglês é a fonte: fica em `docs/`. Cada um dos outros idiomas tem uma pasta com o nome do seu código (`docs/pt-BR/`) com **os mesmos nomes de arquivo** do inglês, mais um arquivo para os textos do próprio site (`docs/.vitepress/locales/pt-BR.mjs`: os títulos da barra lateral, a caixa de pesquisa, o rodapé, os rótulos dos destaques). Uma página ainda não traduzida é um pequeno esboço que mostra um aviso e inclui a página em inglês.

### Traduzindo uma página de um idioma existente

A partir de `docs/`:

```bash
npm install
npm run i18n -- status pt-BR           # what is translated, what is English-only, what is out of date
npm run i18n -- start pt-BR features/users.md
```

O `start` substitui o esboço `docs/pt-BR/features/users.md` por uma cópia da página em inglês. Traduza-a no lugar e depois confira:

```bash
npm test             # the translated pages must keep the English page's structure
npm run dev          # read it in the browser, in your language
```

Abra um pull request quando a página estiver boa de ler; trabalho parcial também é bem-vindo — as páginas em que você não mexeu simplesmente continuam em inglês.

### Adicionando um idioma à documentação

1. Copie `docs/.vitepress/locales/en.mjs` para `docs/.vitepress/locales/<code>.mjs` e traduza: o `name` nativo, os textos do site (`ui`), os rótulos dos destaques (`containers`) e os títulos da barra lateral (`nav`).
2. Registre-o em `docs/.vitepress/locales/index.mjs`.
3. Crie as páginas, como esboços só em inglês: `npm run i18n -- stubs <code>`.
4. Traduza as páginas uma de cada vez com `npm run i18n -- start <code> <page>`.

O idioma aparece no menu de globo e na detecção do idioma do navegador assim que é registrado.

### O que manter e o que traduzir

- **Traduza** o texto, os títulos, as células das tabelas, os títulos dos destaques e os valores `title`/`text` no front matter da página inicial.
- **Mantenha como estão** os blocos de código, o `código` em linha, URLs, variáveis de ambiente, caminhos e nomes de campos da API, nomes de arquivos e pastas, e as chaves do front matter e os valores de `icon:` e `link:`. Traduzir um comentário dentro de um bloco de código é aceitável.
- **Links**: mantenha exatamente os links relativos `.md` da página em inglês (`[Letras](lyrics.md#sidecar-lrc-file)`). Um link para uma página que só existe em inglês continua funcionando. Na página inicial, os links são escritos com o prefixo do idioma (`/pt-BR/features/player/`).
- **Títulos**: mantenha os mesmos títulos, na mesma ordem e nos mesmos níveis. Links para uma seção (`#sidecar-lrc-file`) continuam funcionando em todos os idiomas porque a página traduzida reaproveita os ids de título do inglês — você nunca escreve nem traduz um id.
- **Nomes de botões e configurações**: o app tem a própria tradução de cada rótulo. Use-a, em negrito, para que a página corresponda ao que o leitor vê na tela: procure o rótulo em `frontend/src/i18n/locales/<code>.js`. Se o app ainda não está traduzido nesse idioma, mantenha o rótulo em inglês.
- **Destaques** (`::: tip Título`): mantenha o tipo (`info`, `tip`, `warning`, `danger`) e traduza o título. Um destaque sem título recebe como rótulo a palavra de `containers` no arquivo do idioma.
- **Tom**: escreva para o leitor desse idioma — as páginas são guias, não versões palavra por palavra.

### Mantendo as traduções atualizadas

Quando uma página em inglês muda, as traduções dela não precisam mudar no mesmo pull request: uma página traduzida continua funcionando, e `npm run i18n -- status <code>` lista as páginas cuja fonte em inglês mudou depois de serem traduzidas. Atualizá-las é uma boa primeira contribuição.

Os testes (`npm test` em `docs/`) verificam que todo idioma tem todas as páginas e todo texto do site, e que uma página traduzida ainda tem os títulos, blocos de código, tabelas, destaques e links da página em inglês.
