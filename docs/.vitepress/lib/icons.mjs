// Icons for the docs site, resolved at build time so the client only
// ships the handful it uses. The app's own set (frontend/src/components/
// ui/icons.js) wins; anything it lacks comes from Lucide, which the app's
// icons are drawn to match. Brand marks come from Simple Icons.
import { createRequire } from 'node:module'
import { FILLED, STROKE } from '../../../frontend/src/components/ui/icons.js'

const require = createRequire(import.meta.url)
const lucide = require('@iconify-json/lucide/icons.json')
const simple = require('@iconify-json/simple-icons/icons.json')

// Lucide name (as used in page front matter) → app icon of the same shape.
const APP_ALIASES = {
  house: 'home',
  'sliders-horizontal': 'sliders',
  sparkles: 'sparkle',
  'triangle-alert': 'alert',
  'circle-alert': 'alert',
}

// Front matter written for zensical's other icon packs.
const PACK_ALIASES = {
  'material/api': 'lucide/braces',
  'simple/markdown': 'lucide/file-text',
}

const BRANDS = new Set(['github', 'docker'])

function lucideBody(name) {
  const icon =
    lucide.icons[name] || lucide.icons[lucide.aliases?.[name]?.parent]
  if (!icon) return null
  // Stroke styling comes from the <svg> element, like the app's icons.
  return icon.body
    .replace(
      /\s(?:fill|stroke|stroke-width|stroke-linecap|stroke-linejoin)="[^"]*"/g,
      ''
    )
    .replace(/<g>([\s\S]*)<\/g>/, '$1')
}

/** `lucide/house` or `house` → `{ body, filled }`. */
export function resolveIcon(ref) {
  const full = PACK_ALIASES[ref] || ref
  const name = full.replace(/^lucide\//, '')
  if (BRANDS.has(name)) {
    return {
      body: simple.icons[name].body.replace(/\sfill="[^"]*"/g, ''),
      filled: true,
    }
  }
  const app = APP_ALIASES[name] || name
  if (STROKE[app]) return { body: STROKE[app], filled: false }
  if (FILLED[app]) return { body: FILLED[app], filled: true }
  const body = lucideBody(name)
  if (!body) throw new Error(`Unknown docs icon "${ref}"`)
  return { body, filled: false }
}

/** Icon name (without pack prefix) used by the client. */
export function iconName(ref) {
  return (PACK_ALIASES[ref] || ref).replace(/^lucide\//, '')
}

export function resolveIcons(refs) {
  return Object.fromEntries(
    [...new Set(refs)].map((ref) => [iconName(ref), resolveIcon(ref)])
  )
}
