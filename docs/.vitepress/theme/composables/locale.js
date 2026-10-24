// The language switcher: which languages there are, and where the current
// page is in each of them.
import { computed } from 'vue'
import { useData, useRoute, withBase } from 'vitepress'

/** localStorage key holding the language picked here (see lib/locale-redirect.mjs). */
export const STORAGE_KEY = 'downtify-docs-locale'

export function useLocale() {
  const { site, localeIndex, lang } = useData()
  const route = useRoute()

  // [{ code, name, link }] in the order of the config, English first.
  const locales = computed(() =>
    Object.entries(site.value.locales).map(([key, value]) => ({
      code: key === 'root' ? 'en' : key,
      key,
      name: value.label,
      lang: value.lang,
      link: value.link,
    }))
  )
  const current = computed(
    () =>
      locales.value.find((item) => item.key === localeIndex.value) ||
      locales.value[0]
  )

  /** This page's address in another language. Every language has every page. */
  function hrefFor(target) {
    const here = current.value.link
    const path = route.path.startsWith(withBase(here))
      ? route.path.slice(withBase(here).length)
      : route.path.replace(/^\//, '')
    return withBase(target.link) + path
  }

  /** Remember the pick, so the docs open in it next time. */
  function remember(target) {
    try {
      localStorage.setItem(STORAGE_KEY, target.code)
    } catch {
      // Private mode: the pick lasts for this visit only.
    }
  }

  return { locales, current, hrefFor, remember, lang }
}
