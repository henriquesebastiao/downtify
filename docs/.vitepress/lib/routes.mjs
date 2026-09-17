// Page URLs keep the directory style the site always had
// (`features/player.md` → `/features/player/`), so every page is written
// to `<name>/index.html` and GitHub Pages serves the trailing-slash URL.
import path from 'node:path'

/** VitePress `rewrites` function: source page → output page. */
export function rewritePage(page) {
  if (page === '404.md' || page === 'index.md' || page.endsWith('/index.md')) {
    return page
  }
  return page.replace(/\.md$/, '/index.md')
}

/** Source page (`features/player.md`) → route (`/features/player/`). */
export function pageRoute(page) {
  return `/${rewritePage(page)}`.replace(/index\.md$/, '')
}

const EXTERNAL = /^(?:[a-z][a-z\d+.-]*:|\/\/)/i

/**
 * Markdown links are written relative to the source file
 * (`[Lyrics](../features/lyrics.md#x)`). Rewrites would make VitePress
 * resolve them against the output path instead, so turn every relative
 * `.md` link into the absolute route of its target before VitePress'
 * own link handling (which adds the base and checks for dead links).
 */
export function sourceLinksPlugin(md, srcDir) {
  md.core.ruler.push('downtify_source_links', (state) => {
    const file = state.env.realPath || state.env.path
    if (!file) return
    const dir = path.posix.dirname(
      path.relative(srcDir, file).split(path.sep).join('/')
    )
    for (const block of state.tokens) {
      for (const token of block.children || []) {
        if (token.type !== 'link_open') continue
        const href = token.attrGet('href')
        const rewritten = resolveSourceLink(href, dir)
        if (rewritten) token.attrSet('href', rewritten)
      }
    }
  })
}

/** Relative `.md` link from a page in `dir` → absolute route, or null. */
export function resolveSourceLink(href, dir) {
  if (!href || href.startsWith('#') || href.startsWith('/')) return null
  if (EXTERNAL.test(href)) return null
  const match = /^([^?#]*)(.*)$/.exec(href)
  const target = match[1]
  if (!target.endsWith('.md')) return null
  const page = path.posix.normalize(path.posix.join(dir, target))
  if (page.startsWith('..')) return null
  return pageRoute(page) + match[2]
}
