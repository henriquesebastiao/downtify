<template>
  <UiModal
    :open="Boolean(target)"
    :title="t('origin.title')"
    :description="t('origin.body')"
    width="sm:max-w-xl"
    @close="close"
  >
    <div v-if="target" class="flex flex-col gap-5">
      <p class="truncate text-sm font-semibold" :title="target.file">
        {{ heading }}
      </p>

      <div v-if="loading" class="flex flex-col gap-2" aria-busy="true">
        <div
          v-for="n in 2"
          :key="n"
          class="h-[72px] animate-pulse rounded-[12px] bg-surface-2"
        />
      </div>
      <div
        v-else-if="error"
        class="flex items-center justify-between gap-3"
        role="alert"
      >
        <p class="text-[13px] text-danger">{{ t('origin.failed') }}</p>
        <UiButton variant="ghost" size="sm" icon="refresh" @click="fetch">
          {{ t('common.retry') }}
        </UiButton>
      </div>

      <template v-else-if="answer">
        <section class="flex flex-col gap-2">
          <h3
            class="text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
          >
            {{ t('origin.firstTitle') }}
          </h3>
          <div
            class="rounded-[12px] border border-line-2 bg-surface px-4 py-3 text-sm"
          >
            <template v-if="!origin">
              <p class="text-muted">{{ t('origin.none') }}</p>
            </template>
            <template v-else-if="origin.hidden">
              <p>{{ t('origin.otherAccount') }}</p>
              <p
                class="mt-1 text-[12px] text-muted"
                :title="fullDate(origin.at)"
              >
                {{ when(origin.at) }}
              </p>
            </template>
            <template v-else>
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-semibold">{{ origin.name }}</span>
                <span class="font-mono text-[11.5px] text-faint"
                  >#{{ origin.watch_id }}</span
                >
                <UiBadge v-if="origin.initial">{{
                  t('origin.backfill')
                }}</UiBadge>
                <UiBadge v-if="origin.estimated" tone="warn">{{
                  t('origin.estimated')
                }}</UiBadge>
              </div>
              <p
                class="mt-1 text-[12px] text-muted"
                :title="fullDate(origin.at)"
              >
                {{ when(origin.at)
                }}<template v-if="origin.provider">
                  · {{ providerName(origin.provider) }}</template
                >
              </p>
              <p v-if="!origin.watch" class="mt-2 text-[12px] text-muted">
                {{ t('origin.gone') }}
              </p>
              <div v-else class="mt-3 flex flex-wrap gap-2">
                <UiButton
                  size="sm"
                  variant="secondary"
                  icon="activity"
                  :to="watchRouteFor(origin.watch)"
                  @click="close"
                >
                  {{ t('watchStats.details') }}
                </UiButton>
                <UiButton
                  size="sm"
                  variant="ghost"
                  icon="playlist"
                  :to="libraryRouteFor(origin.watch)"
                  @click="close"
                >
                  {{ t('watchStats.openInLibrary') }}
                </UiButton>
              </div>
            </template>
          </div>
        </section>

        <section class="flex flex-col gap-2">
          <h3
            class="text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
          >
            {{ t('origin.watchesTitle', { count: total }) }}
          </h3>
          <p v-if="!total" class="text-[13px] text-muted">
            {{ t('origin.noWatches') }}
          </p>
          <ul v-else class="flex flex-col gap-2">
            <li
              v-for="watch in answer.watches"
              :key="watch.id"
              class="rounded-[12px] border border-line-2 bg-surface px-4 py-3"
            >
              <div class="flex flex-wrap items-center gap-2">
                <RouterLink
                  :to="watchRouteFor(watch)"
                  class="min-w-0 truncate text-sm font-semibold hover:underline"
                  @click="close"
                  >{{ watch.name }}</RouterLink
                >
                <span class="font-mono text-[11.5px] text-faint"
                  >#{{ watch.id }}</span
                >
                <WatchSourceBadge :source="watch.source" />
                <UiBadge
                  :tone="watch.outcome === 'downloaded' ? 'accent' : 'neutral'"
                >
                  {{ t(`origin.outcome.${watch.outcome}`) }}
                </UiBadge>
              </div>
              <p class="mt-1 text-[12px] text-muted">
                <span :title="fullDate(watch.added_at)">{{
                  when(watch.added_at)
                }}</span>
                <template v-if="watch.owner">
                  · {{ t('sharing.by', { owner: watch.owner }) }}</template
                >
                <template v-if="!watch.enabled">
                  · {{ t('monitor.activeOff') }}</template
                >
              </p>
              <a
                :href="watch.url"
                target="_blank"
                rel="noopener"
                :title="watch.url"
                class="mt-1 block truncate font-mono text-[11.5px] text-muted hover:text-fg hover:underline"
                >{{ watch.url }}</a
              >
            </li>
          </ul>
          <p v-if="answer.others" class="text-[12px] text-muted">
            {{ t('origin.others', { count: answer.others }) }}
          </p>
          <p v-if="total > 1" class="text-[12px] text-faint">
            {{ t('origin.oneFile') }}
          </p>
        </section>
      </template>
    </div>
  </UiModal>
</template>

<script setup>
// "Where it came from": which Playlist Monitor watch first downloaded a
// library song and every watch that holds it now - see
// GET /api/monitor/provenance and downtify/watch_stats.py.
import { computed, ref, watch } from 'vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiModal from '../ui/UiModal.vue'
import WatchSourceBadge from './WatchSourceBadge.vue'
import monitorAPI from '/src/model/monitor'
import { useTrackOrigin } from '/src/model/trackOrigin'
import { timeAgo } from '/src/lib/format'
import {
  libraryRouteFor,
  providerLabelKey,
  watchRouteFor,
} from '/src/lib/watchStats'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const { target, close } = useTrackOrigin()

const answer = ref(null)
const loading = ref(false)
const error = ref(false)

const heading = computed(() => {
  const track = target.value
  if (!track) return ''
  return track.artist ? `${track.title} · ${track.artist}` : track.title
})
const origin = computed(() => answer.value?.origin || null)
const total = computed(
  () => (answer.value?.watches.length || 0) + (answer.value?.others || 0)
)

function when(at) {
  return at ? timeAgo(at, locale.value) : ''
}

function fullDate(at) {
  const date = new Date(at)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString(locale.value)
}

function providerName(id) {
  const key = providerLabelKey(id)
  return key ? t(key) : id
}

async function fetch() {
  const track = target.value
  if (!track) return
  loading.value = true
  error.value = false
  try {
    const res = await monitorAPI.getTrackProvenance(track.file)
    // Another song may have been opened meanwhile.
    if (target.value === track) answer.value = res.data
  } catch {
    if (target.value === track) error.value = true
  } finally {
    if (target.value === track) loading.value = false
  }
}

watch(target, (track) => {
  answer.value = null
  if (track) fetch()
})
</script>
