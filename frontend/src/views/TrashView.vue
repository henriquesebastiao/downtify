<template>
  <div
    class="mx-auto flex max-w-[1280px] flex-col gap-6 px-4 pt-6 pb-10 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader
      :title="t('trash.title')"
      :subtitle="t('trash.subtitle', { days: capability.retentionDays.value })"
    >
      <UiButton variant="ghost" icon="library" :to="{ name: 'Library' }">
        {{ t('library.backToLibrary') }}
      </UiButton>
      <UiButton
        v-if="ready"
        variant="ghost"
        icon="refresh"
        :loading="loading"
        @click="load"
      >
        <span class="max-sm:sr-only">{{ t('common.refresh') }}</span>
      </UiButton>
    </PageHeader>

    <UiEmpty
      v-if="!auth.isAdmin.value"
      icon="lock"
      :title="t('trash.adminOnly')"
      :body="t('trash.adminOnlyHint')"
    />
    <UiEmpty
      v-else-if="checked && !capability.enabled.value"
      icon="trash"
      :title="t('trash.off')"
      :body="t('trash.offHint')"
    />

    <template v-else-if="ready">
      <div class="flex flex-wrap items-center gap-2">
        <UiSegmented v-model="view" :options="views" show-labels />
        <label
          v-if="view === 'trash'"
          class="flex h-10 min-w-0 flex-1 basis-56 items-center gap-2.5 rounded-control border border-line-2 bg-surface px-3 focus-within:border-accent sm:max-w-xs"
        >
          <AppIcon name="filter" :size="16" class="text-faint" />
          <span class="sr-only">{{ t('trash.search') }}</span>
          <input
            v-model="search"
            type="search"
            :placeholder="t('trash.search')"
            class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
          />
        </label>
        <UiButton
          v-if="view === 'trash' && selected.length"
          variant="primary"
          icon="retry"
          :loading="busy"
          @click="restore(selected)"
        >
          {{ t('trash.restoreSelected', { count: selected.length }) }}
        </UiButton>
      </div>

      <p v-if="error" class="text-[13px] text-danger" role="alert">
        {{ error }}
      </p>

      <template v-if="view === 'trash'">
        <p class="tabular text-[13px] text-muted" aria-live="polite">
          {{ t('trash.summary', { count: total, size: formatBytes(size) }) }}
        </p>
        <UiEmpty
          v-if="!items.length && !loading"
          icon="trash"
          :title="search ? t('trash.noMatch') : t('trash.empty')"
          :body="search ? '' : t('trash.emptyHint')"
        />
        <ul
          v-else
          class="flex flex-col divide-y divide-line-2 overflow-hidden rounded-panel border border-line-2 bg-surface"
        >
          <li
            v-for="item in items"
            :key="item.id"
            class="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3"
          >
            <input
              v-model="selected"
              :value="item.id"
              type="checkbox"
              class="size-4 shrink-0 accent-[var(--color-accent)]"
              :disabled="!restorable(item) || busy"
              :aria-label="t('trash.select', { title: titleOf(item) })"
            />
            <div class="min-w-0 flex-1 basis-60">
              <p class="truncate font-semibold text-fg">{{ titleOf(item) }}</p>
              <p class="truncate text-sm text-muted">
                {{ item.metadata.artist || '—' }}
              </p>
              <p class="tabular mt-0.5 truncate text-[12px] text-faint">
                {{ formatOf(item) }} · {{ formatBytes(item.size) }} ·
                {{ item.file }}
              </p>
              <p v-if="item.error" class="mt-1 text-[12px] text-danger">
                {{ t(trashErrorKey(item.error)) }}
              </p>
            </div>
            <div class="flex shrink-0 flex-col items-end gap-1">
              <UiBadge :tone="STATE_TONES[item.state] || 'neutral'">
                {{ t('trash.states.' + item.state) }}
              </UiBadge>
              <span
                v-if="item.expires_at && item.state === 'trashed'"
                class="tabular text-[12px] text-faint"
              >
                {{ t('trash.keptUntil', { date: date(item.expires_at) }) }}
              </span>
            </div>
            <div class="flex shrink-0 gap-2">
              <UiButton
                v-if="item.state === 'error'"
                size="sm"
                variant="ghost"
                icon="retry"
                :disabled="busy"
                @click="retry(item.id)"
              >
                {{ t('trash.retry') }}
              </UiButton>
              <UiButton
                v-if="restorable(item)"
                size="sm"
                :disabled="busy"
                @click="restore([item.id])"
              >
                {{ t('trash.restore') }}
              </UiButton>
            </div>
          </li>
        </ul>
        <div v-if="total > PAGE" class="flex items-center justify-end gap-2">
          <UiButton
            size="sm"
            variant="ghost"
            icon="chevron-left"
            :disabled="offset === 0 || busy"
            @click="offset -= PAGE"
          >
            {{ t('trash.previous') }}
          </UiButton>
          <UiButton
            size="sm"
            variant="ghost"
            icon-right="chevron-right"
            :disabled="offset + PAGE >= total || busy"
            @click="offset += PAGE"
          >
            {{ t('trash.next') }}
          </UiButton>
        </div>
      </template>

      <template v-else>
        <p class="text-sm text-pretty text-muted">
          {{ t('trash.exclusionsHint') }}
        </p>
        <UiEmpty
          v-if="!exclusions.length && !loading"
          icon="download"
          :title="t('trash.exclusionsEmpty')"
        />
        <ul
          v-else
          class="flex flex-col divide-y divide-line-2 overflow-hidden rounded-panel border border-line-2 bg-surface"
        >
          <li
            v-for="item in exclusions"
            :key="item.id"
            class="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3"
          >
            <div class="min-w-0 flex-1 basis-60">
              <p class="truncate font-semibold text-fg">{{ titleOf(item) }}</p>
              <p class="truncate text-sm text-muted">
                {{ item.metadata.artist || '—' }} · {{ formatOf(item) }}
              </p>
            </div>
            <UiButton
              size="sm"
              icon="download"
              :disabled="busy"
              @click="allow(item)"
            >
              {{ t('trash.allowDownload') }}
            </UiButton>
          </li>
        </ul>
      </template>
    </template>
  </div>
</template>

<script setup>
// The music trash (admins): songs moved out of the library, kept for a
// while and restorable until then, and the expired ones still kept out
// of automatic downloads. Reads /api/v1/library/trash; the moves
// themselves are done by the server's trash worker, so a request shows
// as waiting until the worker has really done it.
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { formatBytes } from '/src/lib/format'
import {
  STATE_TONES,
  restorable,
  trashError,
  trashErrorKey,
  useTrashCapability,
} from '/src/lib/trash'
import { useI18n } from '/src/i18n'

const PAGE = 50
const POLL_MS = 3000

const { t, locale } = useI18n()
const auth = useAuth()
const ui = useUi()
const library = useLibrary()
const capability = useTrashCapability()

const view = ref('trash')
const items = ref([])
const exclusions = ref([])
const selected = ref([])
const total = ref(0)
const size = ref(0)
const offset = ref(0)
const search = ref('')
const error = ref('')
const loading = ref(false)
const busy = ref(false)
const checked = ref(false)
let timer = null
let debounce = null
let disposed = false

const ready = computed(
  () => auth.isAdmin.value && checked.value && capability.canManage.value
)
const views = computed(() => [
  { value: 'trash', label: t('trash.inTrash'), icon: 'trash' },
  { value: 'exclusions', label: t('trash.exclusions'), icon: 'download' },
])

const date = (seconds) =>
  new Date(seconds * 1000).toLocaleDateString(locale.value, {
    dateStyle: 'medium',
  })
const titleOf = (item) => item.metadata?.title || item.file
const formatOf = (item) =>
  String(item.metadata?.codec || item.file.split('.').pop() || '').toUpperCase()

async function load() {
  if (loading.value || !ready.value || disposed) return
  loading.value = true
  try {
    if (view.value === 'trash') {
      const { data } = await API.trashList({
        offset: offset.value,
        limit: PAGE,
        search: search.value,
      })
      if (disposed) return
      items.value = data.items
      total.value = data.total
      size.value = data.size
      selected.value = selected.value.filter((id) =>
        data.items.some((item) => item.id === id && restorable(item))
      )
    } else {
      const { data } = await API.trashExclusions()
      if (disposed) return
      exclusions.value = data.items
    }
    error.value = ''
  } catch (e) {
    error.value = trashError(e, t)
  } finally {
    loading.value = false
  }
}

async function act(request) {
  busy.value = true
  error.value = ''
  try {
    await request()
    selected.value = []
    await load()
    await library.load({ force: true })
  } catch (e) {
    error.value = trashError(e, t)
  } finally {
    busy.value = false
  }
}

function restore(ids) {
  return act(() => API.trashRestore([...ids]))
}

function retry(id) {
  return act(() => API.trashRetry([id]))
}

async function allow(item) {
  const ok = await ui.confirm({
    title: t('trash.allowTitle', { title: titleOf(item) }),
    body: t('trash.allowBody'),
    confirmLabel: t('trash.allowDownload'),
  })
  if (ok) await act(() => API.trashAllowDownload([item.id]))
}

watch(search, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => {
    offset.value = 0
    load()
  }, 300)
})
watch([offset, view], load)

onMounted(async () => {
  await capability.refresh()
  checked.value = true
  load()
  timer = setInterval(() => {
    if (!document.hidden) load()
  }, POLL_MS)
})
onUnmounted(() => {
  disposed = true
  clearInterval(timer)
  clearTimeout(debounce)
})
</script>
