<template>
  <div class="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-6 sm:px-6">
    <PageHeader :title="t('trash.title')" :subtitle="t('trash.help')">
      <UiButton :to="{ name: 'Library' }">{{ t('trash.back') }}</UiButton>
    </PageHeader>
    <p v-if="!auth.isAdmin.value" role="alert">
      {{ t('trash.errors.admin_required') }}
    </p>
    <template v-else>
      <div class="flex flex-wrap items-center gap-3">
        <label class="flex min-w-0 flex-1 flex-col gap-1">
          <span>{{ t('trash.search') }}</span>
          <input
            v-model="search"
            type="search"
            class="rounded-control border border-line-2 bg-surface px-3 py-2"
          />
        </label>
        <UiButton
          :disabled="busy || !selected.length"
          @click="restore(selected)"
          >{{ t('trash.restoreSelected') }}</UiButton
        >
        <UiButton :disabled="busy" @click="load">{{
          t('common.refresh')
        }}</UiButton>
      </div>
      <p aria-live="polite">
        {{
          t('trash.summary', {
            count: total,
            size: (size / 1048576).toFixed(1),
          })
        }}
      </p>
      <p v-if="error" role="alert" class="text-red-400">{{ error }}</p>
      <p v-if="!items.length && !loading">{{ t('trash.empty') }}</p>
      <article
        v-for="item in items"
        :key="item.id"
        class="flex flex-wrap items-start gap-3 rounded-panel border border-line-2 bg-surface p-4"
      >
        <input
          v-model="selected"
          :value="item.id"
          type="checkbox"
          :disabled="!restorable(item) || busy"
          :aria-label="
            t('trash.select', { title: item.metadata.title || item.file })
          "
          class="mt-1"
        />
        <div class="min-w-0 flex-1 basis-52">
          <p class="font-semibold">{{ item.metadata.title || item.file }}</p>
          <p>{{ item.metadata.artist }}</p>
          <p class="break-all text-sm text-muted">
            {{ item.metadata.codec || item.file.split('.').pop() }} ·
            {{ item.file }}
          </p>
          <p class="text-sm">{{ t('trash.states.' + item.state) }}</p>
          <p v-if="item.expires_at" class="text-sm">
            {{ t('trash.expires', { date: date(item.expires_at) }) }}
          </p>
          <p v-if="item.error" class="text-sm text-red-400">
            {{ errorText(item.error) }}
          </p>
        </div>
        <UiButton
          v-if="restorable(item)"
          :disabled="busy"
          @click="restore([item.id])"
          >{{ t('trash.restore') }}</UiButton
        >
        <UiButton
          v-if="item.state === 'error'"
          :disabled="busy"
          @click="retry(item.id)"
          >{{ t('trash.retry') }}</UiButton
        >
      </article>
      <div v-if="total > 50" class="flex gap-3">
        <UiButton :disabled="offset === 0 || busy" @click="offset -= 50">{{
          t('trash.previous')
        }}</UiButton>
        <UiButton
          :disabled="offset + 50 >= total || busy"
          @click="offset += 50"
          >{{ t('trash.next') }}</UiButton
        >
      </div>
      <details @toggle="loadExclusions">
        <summary class="cursor-pointer font-semibold">
          {{ t('trash.exclusions') }}
        </summary>
        <p class="my-3 text-sm text-muted">{{ t('trash.exclusionsHelp') }}</p>
        <div
          v-for="item in exclusions"
          :key="item.id"
          class="flex flex-wrap items-center justify-between gap-3 border-b border-line-2 py-3"
        >
          <span
            >{{ item.metadata.artist }} —
            {{ item.metadata.title || item.file }}</span
          >
          <UiButton :disabled="busy" @click="allow(item.id)">{{
            t('trash.allowDownload')
          }}</UiButton>
        </div>
      </details>
    </template>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useUi } from '/src/model/ui'
import { useLibrary } from '/src/model/library'
import { useI18n, currentLocale } from '/src/i18n'
import UiButton from '/src/components/ui/UiButton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import { trashError } from '/src/lib/trash'

const auth = useAuth(),
  ui = useUi(),
  library = useLibrary()
const { t } = useI18n()
const items = ref([]),
  exclusions = ref([]),
  selected = ref([])
const total = ref(0),
  size = ref(0),
  offset = ref(0),
  search = ref('')
const error = ref(''),
  loading = ref(false),
  busy = ref(false)
let timer,
  debounce,
  disposed = false
const date = (seconds) =>
  new Date(seconds * 1000).toLocaleString(currentLocale.value)
const errorText = (code) =>
  trashError({ response: { data: { detail: { code } } } }, t)
const restorable = (item) =>
  ['trashed', 'error'].includes(item.state) &&
  (!item.expires_at || item.expires_at * 1000 > Date.now())

async function load() {
  if (loading.value || !auth.isAdmin.value || disposed) return
  loading.value = true
  try {
    const { data } = await API.trashList({
      offset: offset.value,
      limit: 50,
      search: search.value,
    })
    if (disposed) return
    items.value = data.items
    total.value = data.total
    size.value = data.size
    selected.value = selected.value.filter((id) =>
      data.items.some((item) => item.id === id && restorable(item))
    )
    error.value = ''
  } catch (e) {
    error.value = trashError(e, t)
  } finally {
    loading.value = false
  }
}
async function act(fn) {
  busy.value = true
  error.value = ''
  try {
    await fn()
    selected.value = []
    await load()
    await library.load({ force: true })
  } catch (e) {
    error.value = trashError(e, t)
  } finally {
    busy.value = false
  }
}
async function restore(ids) {
  await act(() => API.trashRestore([...ids]))
}
async function retry(id) {
  await act(() => API.trashRetry([id]))
}
async function loadExclusions(event) {
  if (!event?.target?.open || !auth.isAdmin.value) return
  try {
    exclusions.value = (await API.trashExclusions()).data.items
  } catch (e) {
    error.value = trashError(e, t)
  }
}
async function allow(id) {
  if (
    !(await ui.confirm({
      title: t('trash.allowDownload'),
      body: t('trash.allowHelp'),
      confirmLabel: t('trash.allowDownload'),
    }))
  )
    return
  await act(async () => {
    await API.trashAllowDownload([id])
    exclusions.value = (await API.trashExclusions()).data.items
  })
}
watch(search, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => {
    offset.value = 0
    void load()
  }, 300)
})
watch(offset, load)
onMounted(() => {
  void load()
  timer = setInterval(() => {
    if (!document.hidden) void load()
  }, 3000)
})
onUnmounted(() => {
  disposed = true
  clearInterval(timer)
  clearTimeout(debounce)
})
</script>
