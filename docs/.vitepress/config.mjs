import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import matter from 'gray-matter'
import { defineConfig } from 'vitepress'
import { checkAnchors } from './lib/check-anchors.mjs'
import { iconName, resolveIcons } from './lib/icons.mjs'
import { llmsText } from './lib/llms.mjs'
import { redirectToLocale } from './lib/locale-redirect.mjs'
import { localeMarkdownPlugin } from './lib/locale-markdown.mjs'
import {
  pageRoute,
  rewritePage,
  sourceLinksPlugin,
  splitLocale,
} from './lib/routes.mjs'
import {
  faqEntries,
  homeGraph,
  jsonLdTag,
  OG_LOCALE,
  pageGraph,
} from './lib/seo.mjs'
import { slugifyWithState } from './lib/slug.mjs'
import { isStub, PAGES } from './lib/translations.mjs'
import {
  LOCALES,
  SOURCE_LOCALE,
  TRANSLATED,
  localePrefix,
} from './locales/index.mjs'
import { NAV } from './nav.mjs'

const here = path.dirname(fileURLToPath(import.meta.url))
const srcDir = path.resolve(here, '..')
const repoRoot = path.resolve(srcDir, '..')

// GitHub Pages serves the site from the custom domain (the project URL
// under github.io redirects to it), so it lives at the domain root:
// a base of '/downtify/' would point every asset at a path that 404s.
const SITE_URL = 'https://downtify.henriquesebastiao.com/'
const BASE = '/'
const REPO = 'https://github.com/henriquesebastiao/downtify'
const DESCRIPTION = LOCALES[SOURCE_LOCALE].description

function frontmatterOf(page) {
  return matter(fs.readFileSync(path.join(srcDir, page), 'utf8')).data
}

/** Where a page lives in a locale: `features/x.md` → `pt-BR/features/x.md`. */
const localePage = (code, page) =>
  code === SOURCE_LOCALE ? page : `${code}/${page}`

// ---------------------------------------------------------------------------
// Search engines, social previews and AI assistants (lib/seo.mjs)
// ---------------------------------------------------------------------------

const VERSION = /__version__\s*=\s*'([^']+)'/.exec(
  fs.readFileSync(path.join(repoRoot, 'downtify/__init__.py'), 'utf8')
)[1]

/** Sidebar pages. Any other page is kept out of search results. */
const LISTED = new Set(PAGES)

/**
 * English page → the languages it is really translated into. A language
 * that only has an "English only" stub shows the English text, so search
 * engines are pointed at the English page (canonical) and the stub stays
 * out of the sitemap and of the page's language alternates.
 */
const TRANSLATIONS = Object.fromEntries(
  PAGES.map((page) => [
    page,
    TRANSLATED.filter((code) => {
      const file = path.join(srcDir, code, page)
      return fs.existsSync(file) && !isStub(file)
    }),
  ])
)

/** Languages (English first) a page is written in. */
const languagesOf = (page) => [SOURCE_LOCALE, ...(TRANSLATIONS[page] || [])]

/** `features/x.md` → `https://downtify…/features/x/`. */
const absoluteUrl = (page) => SITE_URL + pageRoute(page).slice(1)

/** Sitemap URL (`pt-BR/features/x/`) → `{ code, page }` of every page. */
const ROUTES = new Map(
  PAGES.flatMap((page) =>
    Object.keys(LOCALES).map((code) => [
      pageRoute(localePage(code, page)).slice(1),
      { code, page },
    ])
  )
)

/** Each language's home page front matter: headline, video, cards... */
const HOMES = Object.fromEntries(
  Object.keys(LOCALES).map((code) => [
    code,
    frontmatterOf(localePage(code, 'index.md')),
  ])
)

/** A language's social preview (docs/public/assets/og/<code>.png). */
const ogImage = (code) => `${SITE_URL}assets/og/${code}.png`
const ogImageAlt = (code) => `Downtify: ${HOMES[code].hero.headline.join(' ')}`

// The README's screenshots, at their stable address on GitHub.
const SCREENSHOTS = [
  'now-playing',
  'home-dark',
  'library-dark',
  'playlist-dark',
  'karaoke',
  'phones',
].map(
  (name) =>
    `https://raw.githubusercontent.com/henriquesebastiao/downtify/main/assets/readme/${name}.png`
)

// The demo video on the home page (docs/public/assets/media/).
const DEMO_VIDEO = { uploaded: '2026-11-17T19:47:59-04:00', duration: 'PT44S' }

const ROBOTS =
  'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'

/** `[{ name, url }]` from the language's home page to `page`. */
function crumbsFor(code, page, title) {
  const { nav } = LOCALES[code]
  const crumb = (name, target) => ({
    name,
    url: absoluteUrl(localePage(code, target)),
  })
  const crumbs = [crumb(nav.pages['index.md'], 'index.md')]
  if (page.startsWith('features/') && page !== 'features/index.md') {
    crumbs.push(crumb(nav.pages['features/index.md'], 'features/index.md'))
  } else if (
    page === 'database.md' ||
    (page.startsWith('getting-started/') && page !== 'getting-started/index.md')
  ) {
    crumbs.push(
      crumb(nav.groups['Getting Started'], 'getting-started/index.md')
    )
  }
  crumbs.push(crumb(title, page))
  return crumbs
}

/** Structured data of a language's home page. */
function homeData(code, description) {
  const home = HOMES[code]
  const source = fs.readFileSync(
    path.join(srcDir, localePage(code, 'index.md')),
    'utf8'
  )
  return homeGraph({
    site: SITE_URL,
    url: absoluteUrl(localePage(code, 'index.md')),
    lang: LOCALES[code].lang,
    languages: Object.values(LOCALES).map((locale) => locale.lang),
    siteDescription: LOCALES[code].description,
    description,
    version: VERSION,
    downloadUrl: `${REPO}/pkgs/container/downtify`,
    installUrl: absoluteUrl(
      localePage(code, 'getting-started/installation.md')
    ),
    repository: REPO,
    image: ogImage(code),
    screenshots: SCREENSHOTS,
    features: (home.why || []).map((item) => item.title),
    video: home.video && {
      name: ogImageAlt(code),
      description: home.video.label,
      thumbnail: SITE_URL + home.video.poster.replace(/^\//, ''),
      content: SITE_URL + home.video.src.replace(/^\//, ''),
      ...DEMO_VIDEO,
    },
    faq: faqEntries(source),
  })
}

/** Sitemap entries: real translations only, with their alternates. */
function sitemapItems(items) {
  return items.flatMap((item) => {
    const route = ROUTES.get(item.url.replace(/^\//, ''))
    if (!route) return []
    const { code, page } = route
    if (code !== SOURCE_LOCALE && !TRANSLATIONS[page].includes(code)) return []
    const links = languagesOf(page).map((lang) => ({
      lang,
      url: pageRoute(localePage(lang, page)).slice(1),
    }))
    links.push({ lang: 'x-default', url: pageRoute(page).slice(1) })
    return [{ ...item, links }]
  })
}

// Sidebar entries carry the route and the (English) page's front-matter
// icon, with their titles in the locale's language.
const iconRefs = []
function sidebarFor(code) {
  const { nav } = LOCALES[code]
  function navItem({ title, page }) {
    const ref = frontmatterOf(page).icon || 'lucide/file-text'
    iconRefs.push(ref)
    const localized = localePage(code, page)
    return {
      title: nav.pages[page] || title,
      page: localized,
      link: pageRoute(localized),
      icon: iconName(ref),
    }
  }
  return NAV.map((entry) => {
    if (!entry.items) return navItem(entry)
    // A feature area's icon heads its card on the home page.
    if (entry.icon) iconRefs.push(entry.icon)
    return {
      title: nav.groups[entry.title] || entry.title,
      icon: entry.icon ? iconName(entry.icon) : undefined,
      items: entry.items.map(navItem),
    }
  })
}

/** One locale's share of the VitePress `locales` option. */
function localeConfig(code) {
  const data = LOCALES[code]
  return {
    label: data.name,
    lang: data.lang,
    link: localePrefix(code),
    title: 'Downtify',
    titleTemplate: `:title · ${data.titleSuffix}`,
    description: data.description,
    themeConfig: { sidebar: sidebarFor(code), ui: data.ui },
  }
}

const UI_ICONS = [
  'search',
  'menu',
  'x',
  'sun',
  'moon',
  'monitor',
  'github',
  'docker',
  'arrow-left',
  'arrow-right',
  'arrow-up-right',
  'pencil',
  'clock',
  'chevron-right',
  'info',
  'lightbulb',
  'triangle-alert',
  'hash',
  'corner-down-left',
  'file-text',
  // Page content (docs/getting-started/index.md, docs/index.md)
  'globe',
  'check',
  'file-code',
  'house',
  'download',
  'play',
  'pause',
  'link',
  'tag',
  'music',
  'radar',
  'server',
  'shield',
  'smartphone',
  'tablet-smartphone',
  'star',
  'heart',
  'languages',
  'git-pull-request',
]

/** First prose paragraph of a page, for <meta name="description">. */
function describe(file) {
  let { content } = matter(fs.readFileSync(file, 'utf8'))
  // A page only available in English includes the English page.
  const include = /<!--@include: ([^>]+?)-->/.exec(content)
  if (include) {
    content = matter(
      fs.readFileSync(
        path.resolve(path.dirname(file), include[1].trim()),
        'utf8'
      )
    ).content
  }
  const paragraph = content
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .find((block) => /^[A-Za-z*`[]/.test(block) && !block.startsWith('|'))
  if (!paragraph) return DESCRIPTION
  const text = paragraph
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/[*_`]/g, '')
    .replace(/\s+/g, ' ')
  return text.length > 160 ? `${text.slice(0, 157).trimEnd()}…` : text
}

// Applied before the first paint, so the page never flashes the wrong theme.
// A reader who never picked a language is sent to the translation their
// browser prefers (English when there is none). See lib/locale-redirect.mjs.
const LOCALE_SCRIPT = `(${redirectToLocale.toString()})(${JSON.stringify(TRANSLATED)},${JSON.stringify(BASE)})`

const THEME_SCRIPT = `(function(){try{var m=localStorage.getItem('downtify-theme');if(m!=='dark'&&m!=='light')m=matchMedia('(prefers-color-scheme: light)').matches?'light':'dark';document.documentElement.setAttribute('data-theme',m);var c=document.querySelector('meta[name=theme-color]');if(c)c.setAttribute('content',m==='light'?'#f6f7f8':'#0b0c0e')}catch(e){}})()`

export default defineConfig({
  // Leftover zensical sample page, not part of the docs.
  srcExclude: ['markdown.md'],
  base: BASE,
  lang: LOCALES[SOURCE_LOCALE].lang,
  title: 'Downtify',
  titleTemplate: `:title · ${LOCALES[SOURCE_LOCALE].titleSuffix}`,
  description: DESCRIPTION,
  locales: {
    root: localeConfig(SOURCE_LOCALE),
    ...Object.fromEntries(TRANSLATED.map((code) => [code, localeConfig(code)])),
  },
  appearance: false,
  lastUpdated: true,
  rewrites: rewritePage,
  // "Open http://localhost:8000" points at the reader's own install.
  ignoreDeadLinks: 'localhostLinks',
  sitemap: { hostname: SITE_URL, transformItems: sitemapItems },

  head: [
    ['link', { rel: 'icon', href: `${BASE}assets/favicon.ico` }],
    [
      'link',
      { rel: 'icon', type: 'image/svg+xml', href: `${BASE}assets/logo.svg` },
    ],
    ['meta', { name: 'theme-color', content: '#0b0c0e' }],
    ['script', {}, THEME_SCRIPT],
    ['script', {}, LOCALE_SCRIPT],
    [
      'link',
      {
        rel: 'apple-touch-icon',
        sizes: '180x180',
        href: `${BASE}assets/apple-touch-icon.png`,
      },
    ],
    ['meta', { property: 'og:site_name', content: 'Downtify' }],
    // Umami page-view analytics for the docs site (cookieless). The
    // Downtify app itself never loads it.
    [
      'script',
      {
        defer: '',
        src: 'https://server.henriquesebastiao.com:8006/script.js',
        'data-website-id': '1ed37e5c-28bf-46bc-b02a-216ab72b7334',
      },
    ],
  ],

  transformPageData(pageData) {
    if (pageData.isNotFound || pageData.frontmatter.description) return
    const file = path.join(srcDir, pageData.filePath)
    if (fs.existsSync(file)) pageData.description = describe(file)
  },

  transformHead({ pageData, title, description }) {
    const { locale, page } = splitLocale(pageData.filePath, TRANSLATED)
    const code = locale || SOURCE_LOCALE
    const image = ogImage(code)
    const social = [
      ['meta', { property: 'og:title', content: title }],
      ['meta', { property: 'og:description', content: description }],
      ['meta', { property: 'og:locale', content: OG_LOCALE[code] }],
      ['meta', { property: 'og:image', content: image }],
      ['meta', { property: 'og:image:type', content: 'image/png' }],
      ['meta', { property: 'og:image:width', content: '1200' }],
      ['meta', { property: 'og:image:height', content: '630' }],
      ['meta', { property: 'og:image:alt', content: ogImageAlt(code) }],
      ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
      ['meta', { name: 'twitter:title', content: title }],
      ['meta', { name: 'twitter:description', content: description }],
      ['meta', { name: 'twitter:image', content: image }],
      ['meta', { name: 'twitter:image:alt', content: ogImageAlt(code) }],
    ]
    // The 404 page and pages outside the sidebar stay out of search results.
    if (pageData.isNotFound || !LISTED.has(page)) {
      return [
        ['meta', { name: 'robots', content: 'noindex, follow' }],
        ['meta', { property: 'og:type', content: 'website' }],
        ...social,
      ]
    }
    // An "English only" stub shows the English page: it speaks for it.
    const translated = !locale || TRANSLATIONS[page].includes(locale)
    const url = absoluteUrl(translated ? pageData.filePath : page)
    const home = pageData.frontmatter.layout === 'home'
    const modified = pageData.lastUpdated
      ? new Date(pageData.lastUpdated).toISOString()
      : undefined
    const tags = [
      ['link', { rel: 'canonical', href: url }],
      ['meta', { name: 'robots', content: ROBOTS }],
      ['meta', { property: 'og:url', content: url }],
      ['meta', { property: 'og:type', content: home ? 'website' : 'article' }],
      ...social,
    ]
    if (!translated) return tags
    // The same page in every language it is written in.
    for (const lang of languagesOf(page)) {
      const href = absoluteUrl(localePage(lang, page))
      tags.push(['link', { rel: 'alternate', hreflang: lang, href }])
      if (lang !== code) {
        tags.push([
          'meta',
          { property: 'og:locale:alternate', content: OG_LOCALE[lang] },
        ])
      }
    }
    tags.push([
      'link',
      { rel: 'alternate', hreflang: 'x-default', href: absoluteUrl(page) },
    ])
    if (home) {
      const poster = HOMES[code].video?.poster
      if (poster) {
        tags.push(['link', { rel: 'preload', as: 'image', href: poster }])
      }
      tags.push(jsonLdTag(homeData(code, description)))
      return tags
    }
    if (modified) {
      tags.push([
        'meta',
        { property: 'article:modified_time', content: modified },
      ])
    }
    tags.push(
      jsonLdTag(
        pageGraph({
          site: SITE_URL,
          url,
          lang: LOCALES[code].lang,
          title: pageData.title,
          description,
          image,
          modified,
          crumbs: crumbsFor(code, page, pageData.title),
        })
      )
    )
    return tags
  },

  markdown: {
    theme: { light: 'github-light', dark: 'github-dark' },
    anchor: { slugifyWithState },
    container: {
      infoLabel: 'Note',
      tipLabel: 'Tip',
      warningLabel: 'Warning',
      dangerLabel: 'Danger',
      detailsLabel: 'Details',
    },
    config(md) {
      sourceLinksPlugin(md, srcDir)
      localeMarkdownPlugin(md, {
        srcDir,
        codes: TRANSLATED,
        labels: Object.fromEntries(
          TRANSLATED.map((code) => [code, LOCALES[code].containers])
        ),
      })
      // Wide tables scroll inside their own box on small screens.
      md.renderer.rules.table_open = () =>
        '<div class="table-wrap" tabindex="0"><table>\n'
      md.renderer.rules.table_close = () => '</table></div>\n'
    },
  },

  themeConfig: {
    icons: resolveIcons([...iconRefs, ...UI_ICONS]),
    search: {
      provider: 'local',
      // Keep section text in the index so results can show an excerpt.
      options: {
        miniSearch: { options: { storeFields: ['title', 'titles', 'text'] } },
      },
    },
    repo: REPO,
    editBase: `${REPO}/edit/main/docs/`,
    social: [
      { icon: 'github', label: 'GitHub', link: REPO },
      {
        icon: 'docker',
        label: 'Docker Hub',
        link: 'https://hub.docker.com/r/henriquesebastiao/downtify',
      },
    ],
    copyright: 'Copyright © 2024 – 2026 Henrique Sebastião',
  },

  vite: {
    plugins: [tailwindcss()],
    // The theme imports the app's design tokens and icons from frontend/.
    server: { fs: { allow: [repoRoot] } },
  },

  buildEnd({ outDir }) {
    const problems = checkAnchors(outDir, BASE)
    if (problems.length) {
      throw new Error(`Broken anchor links:\n  ${problems.join('\n  ')}`)
    }
    // A map of the docs for AI assistants (https://llmstxt.org).
    fs.writeFileSync(
      path.join(outDir, 'llms.txt'),
      llmsText({
        site: SITE_URL,
        nav: NAV,
        titles: LOCALES[SOURCE_LOCALE].nav,
        url: (page) => absoluteUrl(page),
        describe: (page) => describe(path.join(srcDir, page)),
        summary: HOMES[SOURCE_LOCALE].description,
        version: VERSION,
      })
    )
  },
})
