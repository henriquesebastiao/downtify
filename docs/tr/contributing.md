---
icon: lucide/hand-heart
---

# Katkıda bulunma

Katkılar memnuniyetle karşılanır — hata raporları, özellik istekleri, kod ve çeviriler hepsi yardımcı olur. Çeviriler uygulamanın, bu belgelerin ya da ikisinin olabilir: bkz. [Çeviri](#translating).

## Issue’lar ve özellik istekleri

[GitHub issue takipçisini](https://github.com/henriquesebastiao/downtify/issues) kullanın. Yeni bir issue açmadan önce yinelemelerden kaçınmak için mevcutlarda arama yapın.

Hata raporlarına şunları ekleyin:

- Downtify sürümü
- Nasıl kurduğunuz (Docker run, Docker Compose, Umbrel, …)
- Yeniden üretme adımları
- Ne beklediğiniz ve ne olduğu
- İlgili günlükler

## Geliştirme ortamı

### Önkoşullar

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (Python paket yöneticisi)
- ffmpeg (`PATH` içinde olmalı)

### Klonlama ve kurulum

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Geliştirme modunda çalıştırma

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

Frontend geliştirme sunucusu API isteklerini arka uca yönlendirir; bu yüzden yalnızca Vite URL’sini açmanız yeterlidir (genellikle `http://localhost:5173`).

### Testleri çalıştırma

```bash
uv run pytest
```

### Frontend’i üretim için derleme

```bash
cd frontend && npm run build
```

Derlenen dosyalar `frontend/dist/` içine düşer ve arka uç tarafından sunulur.

### Belgeler üzerinde çalışma

Belgeler `docs/` içindeki Markdown dosyalarıdır; [VitePress](https://vitepress.dev/) ve tasarım belirteçlerini web uygulamasıyla paylaşan özel bir temayla (`docs/.vitepress/` içinde) statik bir siteye derlenir.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Diğer sayfalara göreli `.md` yollarıyla bağlantı verin (`[Şarkı sözleri](lyrics.md)`) ve vurgu kutuları için `::: tip Başlık` … `:::` kullanın (`info`, `tip`, `warning`, `danger`). Yeni sayfalar kenar çubuğuna `docs/.vitepress/nav.mjs` içinde eklenir (başlıkları `docs/.vitepress/locales/` içindeki her dilin dosyasında). Derleme, ölü bağlantılarda ve var olmayan başlıklara giden bağlantılarda başarısız olur.

`docs/` içindeki İngilizce sayfalar kaynaktır; diğer her dil onları kendi klasöründe yansıtır (`docs/pt-BR/…`). Bir İngilizce sayfayı değiştirdiğinizde çevirileri güncellemek zorunda değilsiniz — çevirmenler takip eder — ama `docs/` içinde `npm test` çalıştırın: yeni bir sayfa her dilde yalnızca İngilizce bir taslak gerektirir (`npm run i18n -- stubs`) ve eksikse testler bunu söyler.

## Proje yapısı

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

## Çeviri

Downtify’ın çevrilecek iki şeyi vardır ve birini — ya da ikisini birden — alabilirsiniz:

| Çevirdiğiniz | Nerede | Kılavuz |
|---------------|-------|-------|
| **Uygulama** (arayüzü) | `frontend/src/i18n/locales/<code>.js` | [Uygulamayı çevirme](features/internationalization.md#translating-the-app) |
| **Belgeler** (bu sayfalar) | `docs/<code>/` ve `docs/.vitepress/locales/<code>.mjs` | [Belgeleri çevirme](features/internationalization.md#translating-the-documentation) |

Bunlar bağımsızdır: bir dil birinde olup diğerinde henüz olmayabilir ve bir pull request yalnızca bir uygulama çevirisi, yalnızca belgeler ya da ikisini birden içerebilir. Kısmi çalışma memnuniyetle karşılanır — çevrilmemiş metinler uygulamada İngilizceye döner, çevrilmemiş sayfalar belgelerde İngilizce kalır.

Belgeler için hızlı başlangıç, `docs/` içinden:

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

Ayrıntılar için [Uluslararasılaştırma](features/internationalization.md) sayfasına bakın: neyin olduğu gibi kalacağı, tamamen yeni bir dilin nasıl ekleneceği ve düğme adlarının uygulamayla eşleşecek şekilde nasıl çevrileceği.

## Pull request’ler

- Depoyu fork’layın ve `main`’den bir dal oluşturun
- Değişiklikleri odaklı tutun — PR başına bir özellik veya düzeltme
- Arka uç mantığına dokunurken test ekleyin veya güncelleyin
- Göndermeden önce `uv run pytest` çalıştırın
- PR’yi `main`’e açın

Downtify işinize yaradıysa GitHub’da bir yıldız bırakmayı düşünün — projenin büyümesine yardımcı olur.
