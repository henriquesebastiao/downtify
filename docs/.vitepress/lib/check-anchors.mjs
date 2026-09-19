// Post-build check: every internal link that points at an anchor
// (`/features/player/#now-playing`, `#section`) must land on an
// element with that id. VitePress' own dead-link check covers pages but
// not anchors.
import fs from 'node:fs'
import path from 'node:path'

function htmlFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory())
      return entry.name === 'assets' ? [] : htmlFiles(full)
    return entry.name.endsWith('.html') ? [full] : []
  })
}

function routeOf(outDir, file, base) {
  const rel = path.relative(outDir, file).split(path.sep).join('/')
  return base + rel.replace(/(^|\/)index\.html$/, '$1')
}

const decode = (text) =>
  decodeURIComponent(text)
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')

export function checkAnchors(outDir, base) {
  const pages = new Map()
  for (const file of htmlFiles(outDir)) {
    const html = fs.readFileSync(file, 'utf8')
    // Only the rendered page body; skip the 404 page's own links.
    const ids = new Set(
      [...html.matchAll(/\sid="([^"]+)"/g)].map((m) => decode(m[1]))
    )
    pages.set(routeOf(outDir, file, base), { file, html, ids })
  }

  const problems = []
  for (const [route, { html }] of pages) {
    if (route.endsWith('404.html')) continue
    for (const [, href] of html.matchAll(/<a\b[^>]*?\shref="([^"]+)"/g)) {
      const hash = href.indexOf('#')
      if (hash < 0) continue
      const target = href.slice(0, hash)
      const anchor = decode(href.slice(hash + 1))
      if (!anchor) continue
      if (target && !target.startsWith(base)) continue
      const page = pages.get(target || route)
      if (!page) {
        problems.push(`${route}: link to missing page ${href}`)
      } else if (!page.ids.has(anchor)) {
        problems.push(`${route}: missing anchor ${href}`)
      }
    }
  }
  return [...new Set(problems)]
}
