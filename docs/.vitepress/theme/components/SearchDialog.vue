<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="search.open.value"
        class="fixed inset-0 z-[60] flex items-start justify-center bg-black/55 px-3 pt-[8vh] backdrop-blur-sm sm:px-6"
        @click.self="search.hide()"
      >
        <div
          ref="panel"
          role="dialog"
          aria-modal="true"
          aria-label="Search the docs"
          class="flex max-h-[80vh] w-full max-w-[640px] animate-rise flex-col overflow-hidden rounded-panel border border-line-3 bg-surface shadow-float"
          @keydown="onKeydown"
        >
          <label
            class="flex h-14 shrink-0 items-center gap-3 border-b border-line-2 px-4"
          >
            <Icon name="search" :size="19" class="text-muted" />
            <span class="sr-only">Search</span>
            <input
              ref="input"
              v-model="query"
              type="search"
              role="combobox"
              aria-controls="search-results"
              :aria-expanded="results.length > 0"
              :aria-activedescendant="
                results.length ? `search-result-${selected}` : undefined
              "
              autocomplete="off"
              spellcheck="false"
              placeholder="Search the docs"
              class="h-full min-w-0 flex-1 bg-transparent text-[15px] text-fg outline-none placeholder:text-faint [&::-webkit-search-cancel-button]:hidden"
            />
            <button
              type="button"
              class="rounded-md border border-line-3 px-1.5 py-0.5 text-[11px] font-semibold text-muted hover:text-fg"
              @click="search.hide()"
            >
              Esc
            </button>
          </label>

          <div class="min-h-0 flex-1 overflow-y-auto p-2">
            <p v-if="loading" class="px-3 py-8 text-center text-sm text-muted">
              Loading the index…
            </p>
            <p
              v-else-if="!query.trim()"
              class="px-3 py-8 text-center text-sm text-muted"
            >
              Search every page — settings, endpoints, environment variables…
            </p>
            <p
              v-else-if="!results.length"
              class="px-3 py-8 text-center text-sm text-muted"
            >
              Nothing matches “{{ query.trim() }}”.
            </p>
            <ul v-else id="search-results" role="listbox" aria-label="Results">
              <li
                v-for="(result, i) in results"
                :id="`search-result-${i}`"
                :key="result.id"
                role="option"
                :aria-selected="i === selected"
              >
                <a
                  :href="result.id"
                  tabindex="-1"
                  class="flex items-start gap-3 rounded-control px-3 py-2.5 transition-colors"
                  :class="i === selected ? 'bg-surface-2' : ''"
                  @mouseenter="selected = i"
                  @click="search.hide()"
                >
                  <span
                    class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-[9px] bg-raised"
                    :class="i === selected ? 'text-accent' : 'text-muted'"
                  >
                    <Icon
                      :name="result.anchor ? 'hash' : 'file-text'"
                      :size="16"
                    />
                  </span>
                  <span class="min-w-0 flex-1">
                    <span
                      v-if="result.trail"
                      class="block truncate text-[11px] font-medium text-faint"
                      >{{ result.trail }}</span
                    >
                    <span
                      class="block truncate text-sm font-semibold text-fg"
                      v-html="result.title"
                    />
                    <span
                      v-if="result.excerpt"
                      class="mt-0.5 line-clamp-2 block text-[13px] text-muted"
                      v-html="result.excerpt"
                    />
                  </span>
                  <Icon
                    v-if="i === selected"
                    name="corner-down-left"
                    :size="15"
                    class="mt-1 text-faint"
                  />
                </a>
              </li>
            </ul>
          </div>

          <div
            class="hidden shrink-0 items-center gap-4 border-t border-line-2 px-4 py-2.5 text-[11px] text-faint sm:flex"
          >
            <span
              ><kbd class="kbd">↑</kbd> <kbd class="kbd">↓</kbd> to move</span
            >
            <span><kbd class="kbd">Enter</kbd> to open</span>
            <span><kbd class="kbd">Esc</kbd> to close</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import localSearchIndex from '@localSearchIndex'
import MiniSearch from 'minisearch'
import { computed, markRaw, nextTick, ref, shallowRef, watch } from 'vue'
import { useData, useRouter, withBase } from 'vitepress'
import Icon from './Icon.vue'
import { useSearch } from '../composables/search'
import { trapTab } from '../focus'

const search = useSearch()
const router = useRouter()
const { localeIndex, theme } = useData()

const query = ref('')
const selected = ref(0)
const loading = ref(false)
const index = shallowRef(null)
const panel = ref(null)
const input = ref(null)
let returnFocus = null

async function loadIndex() {
  if (index.value || loading.value) return
  loading.value = true
  try {
    const data = (await localSearchIndex[localeIndex.value]?.())?.default
    index.value = markRaw(
      MiniSearch.loadJSON(data, {
        fields: ['title', 'titles', 'text'],
        storeFields: ['title', 'titles', 'text'],
        searchOptions: {
          fuzzy: 0.2,
          prefix: true,
          boost: { title: 4, text: 2, titles: 1 },
        },
      })
    )
  } finally {
    loading.value = false
  }
}

watch(search.open, async (open) => {
  document.documentElement.style.overflow = open ? 'hidden' : ''
  if (!open) {
    returnFocus?.focus?.()
    return
  }
  returnFocus = document.activeElement
  loadIndex()
  await nextTick()
  input.value?.focus()
  input.value?.select()
})

watch(query, () => (selected.value = 0))

const escapeHtml = (text) =>
  text.replace(
    /[&<>"']/g,
    (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[
        c
      ]
  )

function highlight(text, terms) {
  const safe = escapeHtml(text)
  if (!terms.length) return safe
  const pattern = new RegExp(
    `(${terms.map((t) => escapeHtml(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
    'gi'
  )
  return safe.replace(pattern, '<mark>$1</mark>')
}

function excerpt(text, terms) {
  if (!text) return ''
  const lower = text.toLowerCase()
  const at = Math.min(
    ...terms.map((t) => lower.indexOf(t.toLowerCase())).filter((i) => i >= 0),
    Infinity
  )
  const start = at === Infinity ? 0 : Math.max(0, at - 50)
  const slice = text.slice(start, start + 180).trim()
  return (start ? '…' : '') + slice + (start + 180 < text.length ? '…' : '')
}

// Index titles are stored as HTML; turn them back into plain text.
function stripTags(html) {
  const el = document.createElement('div')
  el.innerHTML = html
  return el.textContent.trim()
}

// Section text is plain text with HTML entities left in.
function decodeEntities(text) {
  const el = document.createElement('textarea')
  el.innerHTML = text || ''
  return el.value
}

const results = computed(() => {
  const q = query.value.trim()
  if (!q || !index.value) return []
  const pages = theme.value.sidebar.flatMap((e) => e.items || [e])
  return index.value
    .search(q)
    .slice(0, 24)
    .map((hit) => {
      const terms = hit.terms
      const [path, anchor] = hit.id.split('#')
      const page = pages.find((p) => withBase(p.link) === path)
      const titles = hit.titles.map(stripTags).filter(Boolean)
      const trail = [page?.title, ...titles.slice(1)]
        .filter((t, i, all) => t && all.indexOf(t) === i)
        .join(' › ')
      return {
        id: hit.id,
        anchor,
        trail: anchor ? trail : page?.group || '',
        title: highlight(stripTags(hit.title), terms),
        excerpt: highlight(excerpt(decodeEntities(hit.text), terms), terms),
      }
    })
})

function scrollSelected() {
  nextTick(() =>
    panel.value
      ?.querySelector(`#search-result-${selected.value}`)
      ?.scrollIntoView({ block: 'nearest' })
  )
}

function onKeydown(event) {
  const count = results.value.length
  if (event.key === 'Escape') {
    event.preventDefault()
    search.hide()
  } else if (event.key === 'ArrowDown' && count) {
    event.preventDefault()
    selected.value = (selected.value + 1) % count
    scrollSelected()
  } else if (event.key === 'ArrowUp' && count) {
    event.preventDefault()
    selected.value = (selected.value - 1 + count) % count
    scrollSelected()
  } else if (event.key === 'Enter' && count) {
    event.preventDefault()
    const target = results.value[selected.value]
    search.hide()
    router.go(target.id)
  } else {
    trapTab(event, panel.value)
  }
}
</script>
