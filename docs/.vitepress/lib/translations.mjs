// Which pages the docs have, and which translations are only "English
// only" stubs. Shared by the build (config.mjs) and the translators'
// helper (scripts/i18n.mjs).
import fs from 'node:fs'
import { NAV } from '../nav.mjs'

/** Every sidebar page, as its English Markdown file. */
export const PAGES = NAV.flatMap((entry) =>
  entry.items ? entry.items.map((item) => item.page) : [entry.page]
)

const INCLUDE = /<!--@include: [^>]+-->/

/** Whether a translated page is a stub that shows the English page. */
export function isStub(file) {
  const text = fs.readFileSync(file, 'utf8')
  return INCLUDE.test(text) && text.includes('<EnglishOnly />')
}
