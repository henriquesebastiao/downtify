import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import matter from 'gray-matter'
import { defineConfig } from 'vitepress'
import { checkAnchors } from './lib/check-anchors.mjs'
import { iconName, resolveIcons } from './lib/icons.mjs'
import { redirectToLocale } from './lib/locale-redirect.mjs'
import { localeMarkdownPlugin } from './lib/locale-markdown.mjs'
import {
  pageRoute,
  rewritePage,
  sourceLinksPlugin,
  splitLocale,
} from './lib/routes.mjs'
import { slugifyWithState } from './lib/slug.mjs'
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
  return NAV.map((entry) =>
    entry.items
      ? {
          title: nav.groups[entry.title] || entry.title,
          items: entry.items.map(navItem),
        }
      : navItem(entry)
  )
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
  'eye',
  'sliders-horizontal',
  'mic-vocal',
  'headphones',
  'list-music',
  'folder',
  'import',
  'download',
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
  sitemap: { hostname: SITE_URL },

  head: [
    ['link', { rel: 'icon', href: `${BASE}assets/favicon.ico` }],
    [
      'link',
      { rel: 'icon', type: 'image/svg+xml', href: `${BASE}assets/logo.svg` },
    ],
    ['meta', { name: 'theme-color', content: '#0b0c0e' }],
    ['script', {}, THEME_SCRIPT],
    ['script', {}, LOCALE_SCRIPT],
    ['meta', { property: 'og:site_name', content: 'Downtify' }],
    ['meta', { property: 'og:type', content: 'website' }],
    [
      'meta',
      { property: 'og:image', content: `${SITE_URL}assets/social-image.png` },
    ],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    [
      'meta',
      { name: 'twitter:image', content: `${SITE_URL}assets/social-image.png` },
    ],
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
    const tags = [
      ['meta', { property: 'og:title', content: title }],
      ['meta', { property: 'og:description', content: description }],
      ['meta', { name: 'twitter:title', content: title }],
      ['meta', { name: 'twitter:description', content: description }],
    ]
    if (pageData.isNotFound) return tags
    const url = SITE_URL + pageRoute(pageData.filePath).slice(1)
    // The same page in every language, for search engines.
    const { page } = splitLocale(pageData.filePath, TRANSLATED)
    const alternates = Object.keys(LOCALES).map((code) => [
      'link',
      {
        rel: 'alternate',
        hreflang: code,
        href: SITE_URL + pageRoute(localePage(code, page)).slice(1),
      },
    ])
    return [
      ['link', { rel: 'canonical', href: url }],
      ...alternates,
      [
        'link',
        {
          rel: 'alternate',
          hreflang: 'x-default',
          href: SITE_URL + pageRoute(page).slice(1),
        },
      ],
      ['meta', { property: 'og:url', content: url }],
      ...tags,
    ]
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
  },
})
