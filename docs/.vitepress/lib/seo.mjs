// What search engines, social networks and AI assistants read about each
// page: structured data (schema.org JSON-LD), Open Graph locales and the
// plain text they are built from. Pure functions, used by config.mjs and
// tested in tests/seo.test.mjs.

/** Locale code → Open Graph locale (`og:locale`). */
export const OG_LOCALE = {
  en: 'en_US',
  bg: 'bg_BG',
  de: 'de_DE',
  el: 'el_GR',
  es: 'es_ES',
  fr: 'fr_FR',
  hu: 'hu_HU',
  ko: 'ko_KR',
  'pt-BR': 'pt_BR',
  ru: 'ru_RU',
  tr: 'tr_TR',
  'zh-CN': 'zh_CN',
}

/** Markdown (a paragraph or a few) → plain text. */
export function plainText(markdown) {
  return String(markdown)
    .replace(/<[^>]+>/g, '')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/(\*\*|__)(.+?)\1/g, '$2')
    .replace(/(^|[\s(])[*_]([^*_\n]+)[*_](?=[\s).,;:!?]|$)/g, '$1$2')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * The questions of a page written as `::: details Question` callouts, with
 * their answers as plain text: `[{ question, answer }]`.
 */
export function faqEntries(source) {
  const entries = []
  const block = /^:::\s*details\s+(.+)\n([\s\S]*?)^:::\s*$/gm
  for (const [, question, answer] of String(source).matchAll(block)) {
    entries.push({ question: plainText(question), answer: plainText(answer) })
  }
  return entries
}

/** Site-wide ids, so pages can point at the same entities. */
export function ids(site) {
  return {
    website: `${site}#website`,
    software: `${site}#software`,
    author: `${site}#author`,
  }
}

const AUTHOR = {
  name: 'Henrique Sebastião',
  url: 'https://github.com/henriquesebastiao',
}

/**
 * Structured data for a home page: the site, the app itself, its demo
 * video and the questions the page answers.
 */
export function homeGraph(home) {
  const id = ids(home.site)
  const graph = [
    {
      '@type': 'Person',
      '@id': id.author,
      name: AUTHOR.name,
      url: AUTHOR.url,
    },
    {
      '@type': 'WebSite',
      '@id': id.website,
      url: home.site,
      name: 'Downtify',
      description: home.siteDescription,
      inLanguage: home.languages,
      publisher: { '@id': id.author },
    },
    {
      '@type': 'SoftwareApplication',
      '@id': id.software,
      name: 'Downtify',
      url: home.url,
      description: home.description,
      applicationCategory: 'MultimediaApplication',
      applicationSubCategory: 'Music downloader',
      operatingSystem: 'Linux (Docker image for amd64 and arm64)',
      softwareVersion: home.version,
      downloadUrl: home.downloadUrl,
      installUrl: home.installUrl,
      license: 'https://www.gnu.org/licenses/agpl-3.0.html',
      isAccessibleForFree: true,
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
      image: home.image,
      screenshot: home.screenshots,
      featureList: home.features,
      author: { '@id': id.author },
      sameAs: [home.repository],
    },
  ]
  if (home.video) {
    graph.push({
      '@type': 'VideoObject',
      name: home.video.name,
      description: home.video.description,
      thumbnailUrl: home.video.thumbnail,
      contentUrl: home.video.content,
      uploadDate: home.video.uploaded,
      duration: home.video.duration,
      inLanguage: 'en',
    })
  }
  if (home.faq?.length) {
    graph.push({
      '@type': 'FAQPage',
      inLanguage: home.lang,
      mainEntity: home.faq.map(({ question, answer }) => ({
        '@type': 'Question',
        name: question,
        acceptedAnswer: { '@type': 'Answer', text: answer },
      })),
    })
  }
  return { '@context': 'https://schema.org', '@graph': graph }
}

/**
 * Structured data for a documentation page: the article and where it sits
 * (`crumbs`: `[{ name, url }]`, the page itself last).
 */
export function pageGraph(page) {
  const id = ids(page.site)
  const article = {
    '@type': 'TechArticle',
    headline: page.title,
    description: page.description,
    url: page.url,
    inLanguage: page.lang,
    image: page.image,
    isPartOf: { '@id': id.website },
    about: { '@id': id.software },
    author: { '@id': id.author },
    publisher: { '@id': id.author },
  }
  if (page.modified) article.dateModified = page.modified
  const graph = [article]
  if (page.crumbs?.length > 1) {
    graph.push({
      '@type': 'BreadcrumbList',
      itemListElement: page.crumbs.map((crumb, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: crumb.name,
        item: crumb.url,
      })),
    })
  }
  return { '@context': 'https://schema.org', '@graph': graph }
}

/** A JSON-LD `<script>` for VitePress `head`, safe inside HTML. */
export function jsonLdTag(data) {
  const json = JSON.stringify(data).replace(/</g, '\\u003c')
  return ['script', { type: 'application/ld+json' }, json]
}
