---
icon: lucide/hand-heart
---

# Contribuindo

Contribuições são bem-vindas — relatos de bugs, pedidos de funcionalidades, código e traduções ajudam. As traduções podem ser do app, desta documentação, ou de ambos: veja [Traduzindo](#translating).

## Issues e pedidos de funcionalidades

Use o [rastreador de issues do GitHub](https://github.com/henriquesebastiao/downtify/issues). Antes de abrir uma nova issue, pesquise as existentes para evitar duplicatas.

Em relatos de bugs, inclua:

- Versão do Downtify
- Como você instalou (Docker run, Docker Compose, Umbrel, …)
- Passos para reproduzir
- O que você esperava e o que aconteceu
- Quaisquer logs relevantes

## Ambiente de desenvolvimento

### Pré-requisitos

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (gerenciador de pacotes Python)
- ffmpeg (precisa estar no `PATH`)

### Clonar e instalar

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Executar em modo de desenvolvimento

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

O servidor de desenvolvimento do frontend encaminha as requisições de API para o backend, então você só precisa abrir a URL do Vite (normalmente `http://localhost:5173`).

### Executar os testes

```bash
uv run pytest
```

### Gerar o frontend para produção

```bash
cd frontend && npm run build
```

Os arquivos compilados ficam em `frontend/dist/` e são servidos pelo backend.

### Trabalhar na documentação

A documentação são arquivos Markdown em `docs/`, transformados em um site estático com o [VitePress](https://vitepress.dev/) e um tema personalizado (em `docs/.vitepress/`) que compartilha seus tokens de design com o app web.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Faça links para outras páginas com caminhos `.md` relativos (`[Letras](lyrics.md)`) e use `::: tip Título` … `:::` para destaques (`info`, `tip`, `warning`, `danger`). Páginas novas entram na barra lateral em `docs/.vitepress/nav.mjs` (com o título delas no arquivo de cada idioma em `docs/.vitepress/locales/`). A compilação falha com links quebrados e com links para títulos que não existem.

As páginas em inglês em `docs/` são a fonte; cada um dos outros idiomas as espelha em uma pasta própria (`docs/pt-BR/…`). Você não precisa atualizar as traduções ao mudar uma página em inglês — os tradutores acompanham —, mas rode `npm test` em `docs/`: uma página nova precisa de um esboço só em inglês em cada idioma (`npm run i18n -- stubs`), e os testes avisam se ele estiver faltando.

## Estrutura do projeto

```
downtify/
├── downtify/          # Python backend
│   ├── api.py         # FastAPI router
│   ├── downloader.py  # yt-dlp + mutagen pipeline
│   ├── spotify.py     # Spotify embed scraping
│   ├── providers.py   # YouTube Music search
│   ├── monitor.py     # Playlist monitor
│   ├── lyrics.py      # lrclib integration
│   └── m3u.py         # M3U generation
├── frontend/          # Vue 3 + Vite frontend
│   └── src/
│       └── i18n/      # Translation files
├── docs/              # This documentation (Markdown + VitePress site)
│   ├── <page>.md      # English, the source
│   ├── pt-BR/ …       # One folder per translated language, same file names
│   └── .vitepress/
│       └── locales/   # Each language's site text and sidebar titles
├── main.py            # Entry point
├── Dockerfile
└── docker-compose.yml
```

## Traduzindo

O Downtify tem duas coisas para traduzir, e você pode pegar qualquer uma — ou as duas:

| Você traduz | Onde | Guia |
|---------------|-------|-------|
| **O app** (a interface dele) | `frontend/src/i18n/locales/<code>.js` | [Traduzindo o app](features/internationalization.md#translating-the-app) |
| **A documentação** (estas páginas) | `docs/<code>/` e `docs/.vitepress/locales/<code>.mjs` | [Traduzindo a documentação](features/internationalization.md#translating-the-documentation) |

Elas são independentes: um idioma pode estar em uma e ainda não na outra, e um pull request pode conter só a tradução do app, só a documentação, ou ambas. Trabalho parcial é bem-vindo — textos não traduzidos voltam ao inglês no app, e páginas não traduzidas continuam em inglês na documentação.

Início rápido para a documentação, a partir de `docs/`:

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

Veja [Internacionalização](features/internationalization.md) para os detalhes: o que manter como está, como adicionar um idioma novo inteiro e como traduzir os nomes de botões para que coincidam com os do app.

## Pull requests

- Faça um fork do repositório e crie uma branch a partir da `main`
- Mantenha as mudanças focadas — uma funcionalidade ou correção por PR
- Adicione ou atualize testes ao mexer na lógica do backend
- Rode `uv run pytest` antes de enviar
- Abra o PR contra a `main`

Se o Downtify foi útil para você, considere deixar uma estrela no GitHub — isso ajuda o projeto a crescer.
