// The sidebar tree from config.mjs, plus where the current page sits in it.
import { computed } from 'vue'
import { useData } from 'vitepress'

export function useNav() {
  const { theme, page } = useData()

  const sidebar = computed(() => theme.value.sidebar)
  const pages = computed(() =>
    sidebar.value.flatMap((entry) =>
      entry.items
        ? entry.items.map((item) => ({ ...item, group: entry.title }))
        : [entry]
    )
  )
  const current = computed(() =>
    pages.value.find((item) => item.page === page.value.filePath)
  )
  const position = computed(() => pages.value.indexOf(current.value))
  // Home is the landing page, not a step in the reading order.
  const prev = computed(() =>
    position.value > 1 ? pages.value[position.value - 1] : null
  )
  const next = computed(() =>
    position.value >= 0 ? pages.value[position.value + 1] || null : null
  )

  const isActive = (item) => item.page === page.value.filePath

  return { sidebar, pages, current, prev, next, isActive }
}
