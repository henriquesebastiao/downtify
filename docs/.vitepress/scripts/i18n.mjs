#!/usr/bin/env node
// Helper for translating the documentation. Run from docs/ (or through
// `npm run i18n -- <command>`):
//
//   status [locale]         how much of each language is translated, and
//                           which translations are older than their English page
//   stubs [locale]          create the pages a language is missing, as "English
//                           only" stubs, so every language has every page
//   start <locale> <page>   replace a stub with a copy of the English page, ready
//                           to translate (page: `features/users.md`)
//
// English is the source and lives in docs/; a language `xx` lives in docs/xx/
// with the same file names. See "Translating the docs" in Contributing.
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import matter from 'gray-matter'
import { LOCALES, TRANSLATED } from '../locales/index.mjs'
import { NAV } from '../nav.mjs'

const docsDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..',
  '..'
)

export const PAGES = NAV.flatMap((entry) =>
  entry.items ? entry.items.map((item) => item.page) : [entry.page]
)

const INCLUDE = /<!--@include: [^>]+-->/

/** The Markdown of a page "only available in English". */
export function stubFor(page) {
  const { data } = matter(fs.readFileSync(path.join(docsDir, page), 'utf8'))
  const depth = page.split('/').length // the stub sits one folder deeper
  const up = '../'.repeat(depth)
  const icon = data.icon ? `icon: ${data.icon}\n` : ''
  return `---\n${icon}---\n\n<EnglishOnly />\n\n<!--@include: ${up}${page}-->\n`
}

export const isStub = (file) =>
  INCLUDE.test(fs.readFileSync(file, 'utf8')) &&
  fs.readFileSync(file, 'utf8').includes('<EnglishOnly />')

function commitTime(file) {
  try {
    const out = execFileSync('git', ['log', '-1', '--format=%ct', '--', file], {
      cwd: docsDir,
      encoding: 'utf8',
    }).trim()
    return out ? Number(out) : 0
  } catch {
    return 0
  }
}

function localesFrom(arg) {
  if (!arg) return TRANSLATED
  if (!TRANSLATED.includes(arg)) {
    throw new Error(
      `Unknown language "${arg}". Use one of: ${TRANSLATED.join(', ')}`
    )
  }
  return [arg]
}

function status(arg) {
  for (const code of localesFrom(arg)) {
    const done = []
    const missing = []
    const outdated = []
    for (const page of PAGES) {
      const file = path.join(docsDir, code, page)
      if (!fs.existsSync(file)) missing.push(page)
      else if (isStub(file)) continue
      else {
        done.push(page)
        const en = commitTime(path.join(docsDir, page))
        const tr = commitTime(file)
        if (en && tr && en > tr) outdated.push(page)
      }
    }
    const stubs = PAGES.length - done.length - missing.length
    console.log(
      `${code.padEnd(6)} ${LOCALES[code].name}: ${done.length}/${PAGES.length} translated, ${stubs} English-only, ${missing.length} missing`
    )
    if (arg) {
      for (const page of missing) console.log(`  missing   ${page}`)
      for (const page of outdated)
        console.log(`  outdated  ${page} (English changed after it)`)
    } else if (outdated.length) {
      console.log(
        `       ${outdated.length} older than the English page (run with the language for the list)`
      )
    }
  }
}

function stubs(arg) {
  let made = 0
  for (const code of localesFrom(arg)) {
    for (const page of PAGES) {
      const file = path.join(docsDir, code, page)
      if (fs.existsSync(file)) continue
      fs.mkdirSync(path.dirname(file), { recursive: true })
      fs.writeFileSync(file, stubFor(page))
      made++
    }
  }
  console.log(`Created ${made} English-only page(s).`)
}

function start(code, page) {
  if (!code || !page) throw new Error('Usage: i18n start <language> <page>')
  localesFrom(code)
  if (!PAGES.includes(page)) throw new Error(`Unknown page "${page}"`)
  const file = path.join(docsDir, code, page)
  if (fs.existsSync(file) && !isStub(file)) {
    throw new Error(`${code}/${page} is already translated`)
  }
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.copyFileSync(path.join(docsDir, page), file)
  console.log(
    `Copied ${page} to ${code}/${page} — translate it, keeping links, code and front matter keys as they are.`
  )
}

const [command, ...args] = process.argv.slice(2)
if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    if (command === 'status') status(args[0])
    else if (command === 'stubs') stubs(args[0])
    else if (command === 'start') start(args[0], args[1])
    else {
      console.log(
        'Usage: i18n <status [language] | stubs [language] | start <language> <page>>'
      )
      process.exitCode = command ? 1 : 0
    }
  } catch (error) {
    console.error(error.message)
    process.exitCode = 1
  }
}
