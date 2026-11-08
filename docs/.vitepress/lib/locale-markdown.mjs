// Markdown behaviour that only translated pages need.
//
// - Heading ids. A translated heading would get an id in its own language
//   (`## Compartilhar playlists` → `#compartilhar-playlists`), which would
//   break every link written against the English ids (`users.md#sharing-playlists`).
//   Translated pages keep the English page's ids instead, heading by
//   heading, so a link works the same in every language and translators
//   never have to think about anchors.
// - Callout labels. `::: tip` without a title is labelled "Tip" in English;
//   other languages label it in their own words (`containers` in the
//   locale file).
import fs from 'node:fs'
import path from 'node:path'
import matter from 'gray-matter'
import { splitLocale } from './routes.mjs'

const CONTAINER = /^container_(info|tip|warning|danger|details)_open$/

/**
 * @param md      the markdown-it instance
 * @param options `{ srcDir, codes, labels }`: the docs folder, the codes of
 *                the translated locales, and `{ code: containers }`
 */
export function localeMarkdownPlugin(md, { srcDir, codes, labels }) {
  const idsByPage = new Map()

  /** Heading ids of an English page, in document order. */
  function englishIds(page) {
    if (!idsByPage.has(page)) {
      const file = path.join(srcDir, page)
      let ids = []
      if (fs.existsSync(file)) {
        const { content } = matter(fs.readFileSync(file, 'utf8'))
        const env = { path: file }
        ids = md
          .parse(content, env)
          .filter((token) => token.type === 'heading_open')
          .map((token) => token.attrGet('id'))
      }
      idsByPage.set(page, ids)
    }
    return idsByPage.get(page)
  }

  md.core.ruler.before('anchor', 'downtify_locale', (state) => {
    // The source file, not the output page (`rewrites` moves those).
    const file = state.env.realPath || state.env.path
    if (!file) return
    const relativePath = path.relative(srcDir, file).split(path.sep).join('/')
    const { locale, page } = splitLocale(relativePath, codes)
    if (!locale) return

    const ids = englishIds(page)
    let heading = 0
    for (const token of state.tokens) {
      if (token.type === 'heading_open') {
        const id = ids[heading++]
        if (id) token.attrSet('id', id)
        continue
      }
      const match = CONTAINER.exec(token.type)
      if (!match) continue
      const kind = match[1]
      const title = token.info.trim().slice(kind.length).trim()
      if (!title && labels[locale]?.[kind]) {
        token.info = `${kind} ${labels[locale][kind]}`
      }
    }
  })
}
