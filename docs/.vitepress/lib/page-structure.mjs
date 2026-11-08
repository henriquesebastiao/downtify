// A page's skeleton - what a translation must keep as the English page has
// it: the headings (levels and order; their ids come from the English
// ones), code blocks, tables, callouts, link targets and front matter
// shape. Used by tests/locales.test.mjs so a translator hears about a
// dropped heading or a mistyped link before the build does.
import matter from 'gray-matter'

const FENCE = /^\s*(```|~~~)/

/** Lines of a page body that are not inside a fenced code block. */
function proseLines(body) {
  const lines = []
  let fence = null
  for (const line of body.split('\n')) {
    const match = FENCE.exec(line)
    if (match) {
      if (!fence) fence = match[1]
      else if (match[1] === fence) fence = null
      continue
    }
    if (!fence) lines.push(line)
  }
  return lines
}

/** Link targets of a page in order, with `/<locale>/` taken off. */
function linkTargets(text, codes) {
  const targets = []
  const link = /\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g
  for (const [, href] of text.matchAll(link)) targets.push(href)
  // Links in HTML-ish Vue props: `link: /features/x/` in front matter.
  return targets.map((href) => stripLocale(href, codes))
}

export function stripLocale(href, codes) {
  for (const code of codes) {
    if (href === `/${code}/`) return '/'
    if (href.startsWith(`/${code}/`)) return href.slice(code.length + 1)
  }
  return href
}

/** Front matter reduced to its shape: keys, array lengths, fixed values. */
function shape(value, codes, key = '') {
  if (Array.isArray(value)) return value.map((item) => shape(item, codes, key))
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k, shape(v, codes, k)])
    )
  }
  // Text is translated; what points somewhere or names an icon is not.
  if (['link', 'icon', 'src', 'primary'].includes(key)) {
    return typeof value === 'string' ? stripLocale(value, codes) : value
  }
  return typeof value
}

export function structureOf(source, codes = []) {
  const { data, content } = matter(source)
  const lines = proseLines(content)
  // Inline code is text, not Markdown or components.
  const prose = lines.join('\n').replace(/`[^`\n]*`/g, '``')
  return {
    frontMatter: shape(data, codes),
    headings: lines
      .map((line) => /^(#{1,6})\s+\S/.exec(line))
      .filter(Boolean)
      .map((match) => match[1].length),
    codeBlocks: [...content.matchAll(/^\s*(?:```|~~~)(\S*)/gm)]
      .filter((_, i) => i % 2 === 0)
      .map((match) => match[1]),
    tableRows: lines.filter((line) => /^\s*\|/.test(line)).length,
    callouts: lines
      .filter((line) => /^:::\s*\S*/.test(line))
      .map((line) => /^:::\s*(\w*)/.exec(line)[1]),
    links: linkTargets(prose, codes),
    components: [...prose.matchAll(/<([A-Z]\w+)/g)].map((match) => match[1]),
  }
}
