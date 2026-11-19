<template>
  <!-- Why downloads didn't come from slskd (admins): GET/DELETE
       /api/slskd/misses. -->
  <UiPanel
    v-if="summary && (summary.total || resetDone)"
    :title="t('slskdMisses.title')"
    :description="t('slskdMisses.hint')"
  >
    <template #actions>
      <UiButton
        size="sm"
        variant="ghost"
        icon="refresh"
        :disabled="!summary.total || resetting"
        @click="reset"
      >
        {{ t('slskdMisses.reset') }}
      </UiButton>
    </template>

    <p v-if="!summary.total" class="text-[13px] text-muted">
      {{ t('slskdMisses.empty') }}
    </p>
    <template v-else>
      <p class="mb-3 text-[12px] text-muted">
        {{
          t('slskdMisses.since', {
            count: summary.total,
            when: timeAgo(summary.since, locale),
          })
        }}
      </p>
      <ul class="flex flex-col gap-3">
        <li v-for="row in rows" :key="row.reason" class="text-sm">
          <button
            type="button"
            class="w-full text-left"
            :aria-expanded="open === row.reason"
            @click="open = open === row.reason ? '' : row.reason"
          >
            <span class="flex items-center justify-between gap-3">
              <span class="truncate">{{
                t(`slskdMisses.reason.${row.reason}`)
              }}</span>
              <span class="tabular text-muted">{{ row.count }}</span>
            </span>
            <span
              class="mt-1 block h-1.5 overflow-hidden rounded-full bg-surface-2"
            >
              <span
                class="block h-full rounded-full bg-warn"
                :style="{ width: `${Math.max(2, row.share * 100)}%` }"
              />
            </span>
          </button>
          <div v-if="open === row.reason" class="mt-2 flex flex-col gap-2">
            <p class="text-[12.5px] text-pretty text-muted">
              {{ t(`slskdMisses.fix.${row.reason}`) }}
            </p>
            <ul class="flex flex-col gap-1.5">
              <li
                v-for="(song, index) in examples(row.reason)"
                :key="index"
                class="flex flex-col text-[12.5px]"
              >
                <span class="truncate font-medium"
                  >{{ song.title
                  }}<span v-if="song.artist" class="font-normal text-muted">
                    · {{ song.artist }}</span
                  ></span
                >
                <span
                  v-if="song.detail"
                  class="truncate font-mono text-[11px] text-faint"
                  :title="song.detail"
                  >{{ song.detail }}</span
                >
              </li>
            </ul>
          </div>
        </li>
      </ul>
      <p class="mt-4 text-[12px] text-muted">
        {{ t('slskdMisses.usedInstead') }} {{ fallbackLine }}
      </p>
    </template>
  </UiPanel>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import API from '/src/model/api'
import { useUi } from '/src/model/ui'
import UiButton from '../ui/UiButton.vue'
import UiPanel from '../ui/UiPanel.vue'
import { fallbackRows, missRows, reasonOf } from '/src/lib/slskdMisses'
import { timeAgo } from '/src/lib/format'
import { useI18n } from '/src/i18n'

// Anything that changes the queue's finished count: a good moment to ask
// again.
const props = defineProps({ finished: { type: Number, default: 0 } })

const { t, locale } = useI18n()
const ui = useUi()
const summary = ref(null)
const open = ref('')
const resetting = ref(false)
const resetDone = ref(false)

const rows = computed(() => missRows(summary.value))
const fallbacks = computed(() => fallbackRows(summary.value))

const SOURCE_NAMES = {
  'youtube-music': 'YouTube Music',
  youtube: 'YouTube',
  soundcloud: 'SoundCloud',
  deemix: 'Deemix',
}

function sourceName(source) {
  return SOURCE_NAMES[source] || source
}

// "YouTube Music 4 · YouTube 1 · nothing found 1"
const fallbackLine = computed(() =>
  fallbacks.value
    .map(
      (row) =>
        `${
          row.source === 'none'
            ? t('slskdMisses.nothingFound')
            : sourceName(row.source)
        } ${row.count}`
    )
    .join(' · ')
)

function examples(reason) {
  return (summary.value?.recent || [])
    .filter((song) => reasonOf(song) === reason)
    .slice(0, 5)
}

async function load() {
  try {
    summary.value = (await API.getSlskdMisses()).data
  } catch {
    summary.value = null
  }
}

async function reset() {
  const ok = await ui.confirm({
    title: t('slskdMisses.resetTitle'),
    body: t('slskdMisses.resetBody'),
    confirmLabel: t('slskdMisses.reset'),
  })
  if (!ok) return
  resetting.value = true
  try {
    await API.resetSlskdMisses()
    resetDone.value = true
    open.value = ''
    await load()
  } finally {
    resetting.value = false
  }
}

let timer = null
let lastLoad = 0

watch(
  () => props.finished,
  () => {
    // At most every 15 s while downloads keep finishing.
    if (Date.now() - lastLoad < 15000) return
    lastLoad = Date.now()
    load()
  }
)

onMounted(() => {
  lastLoad = Date.now()
  load()
  timer = setInterval(load, 60000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>
