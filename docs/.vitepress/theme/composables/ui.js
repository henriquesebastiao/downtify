// The site chrome's text in the page's language (`ui` in the locale file,
// delivered as `theme.ui` by the locale's `themeConfig`). English is the
// fallback so a missing key never renders blank.
import { computed } from 'vue'
import { useData } from 'vitepress'
import en from '../../locales/en.mjs'

export function useUi() {
  const { theme, localeIndex, site } = useData()
  const ui = computed(() => ({ ...en.ui, ...theme.value.ui }))
  /** `t('searchNothing', { query })`. */
  const t = (key, params = {}) =>
    String(ui.value[key] ?? key).replace(/\{(\w+)\}/g, (_, name) =>
      params[name] == null ? `{${name}}` : params[name]
    )
  /** Home of the page's language: `/` or `/pt-BR/`. */
  const home = computed(
    () => site.value.locales[localeIndex.value]?.link || '/'
  )
  return { ui, t, home }
}
