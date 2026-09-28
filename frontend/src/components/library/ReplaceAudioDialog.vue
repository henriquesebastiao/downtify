<template>
  <UiModal
    :open="Boolean(track)"
    :title="t('replace.title')"
    :description="t('replace.body')"
    width="sm:max-w-2xl"
    @close="close"
  >
    <div v-if="track" class="flex flex-col gap-4">
      <!-- The track as it is -->
      <div
        class="flex items-center gap-3 rounded-control border border-line-2 bg-surface-2 px-3 py-2.5"
      >
        <CoverArt
          :src="track.hasCover ? track.cover : ''"
          :name="track.title"
          class="size-11 shrink-0"
          rounded="rounded-[7px]"
          :letter-size="16"
          :icon-size="18"
        />
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="truncate text-sm font-semibold">{{ track.title }}</span>
          <span class="truncate text-[12px] text-muted">
            {{ track.artists.join(', ') || track.artist }}
            <template v-if="length">· {{ formatDuration(length) }}</template>
          </span>
        </span>
        <UiBadge>{{ t('replace.current') }}</UiBadge>
      </div>

      <template v-if="job">
        <!-- Replacing -->
        <div class="flex flex-col gap-2" aria-live="polite">
          <p class="text-sm font-semibold">
            {{
              job.status === 'done'
                ? t('replace.done')
                : job.status === 'error'
                  ? t('replace.failed')
                  : t('replace.running')
            }}
          </p>
          <UiProgress
            v-if="job.status === 'downloading'"
            :value="job.progress"
            :indeterminate="!job.progress"
          />
          <p v-if="job.message" class="text-[13px] text-muted">
            {{ job.message }}
          </p>
        </div>
      </template>

      <template v-else>
        <form class="flex gap-2" @submit.prevent="search">
          <UiInput
            v-model="query"
            class="min-w-0 flex-1"
            :label="t('replace.search')"
            :hint="t('replace.searchHint')"
            icon="search"
          />
          <UiButton
            type="submit"
            class="self-start sm:mt-[26px]"
            :loading="loading"
            :disabled="!query.trim()"
          >
            {{ t('replace.searchButton') }}
          </UiButton>
        </form>

        <p v-if="error" class="text-[13px] text-danger" role="alert">
          {{ error }}
        </p>
        <p
          v-else-if="!loading && searched && !candidates.length"
          class="text-sm text-muted"
        >
          {{ t('replace.none') }}
        </p>

        <ul
          v-if="candidates.length"
          class="flex flex-col gap-1"
          role="radiogroup"
          :aria-label="t('replace.results')"
        >
          <li v-for="item in candidates" :key="item.video_id">
            <div
              role="radio"
              tabindex="0"
              :aria-checked="chosen === item.video_id"
              class="flex cursor-pointer items-center gap-3 rounded-control border px-2.5 py-2 transition-colors"
              :class="
                chosen === item.video_id
                  ? 'border-accent bg-accent/8'
                  : 'border-transparent hover:bg-surface-2'
              "
              @click="chosen = item.video_id"
              @keydown.enter.prevent="chosen = item.video_id"
              @keydown.space.prevent="chosen = item.video_id"
            >
              <img
                :src="item.thumbnail"
                alt=""
                loading="lazy"
                class="h-11 w-[4.5rem] shrink-0 rounded-[6px] bg-surface-2 object-cover"
              />
              <span class="flex min-w-0 flex-1 flex-col">
                <span class="truncate text-sm font-medium">{{
                  item.title
                }}</span>
                <span class="truncate text-[12px] text-muted">
                  {{ [item.artist, item.album].filter(Boolean).join(' · ') }}
                </span>
                <span class="mt-0.5 flex flex-wrap items-center gap-1.5">
                  <UiBadge
                    :tone="item.source === 'youtube' ? 'neutral' : 'ytm'"
                  >
                    {{ t(`replace.source.${item.source}`) }}
                  </UiBadge>
                  <span
                    v-if="item.duration"
                    class="tabular text-[12px]"
                    :class="
                      sameLength(item.duration_diff)
                        ? 'text-accent'
                        : 'text-faint'
                    "
                  >
                    {{ formatDuration(item.duration) }}
                    <template v-if="lengthDiff(item.duration_diff)">
                      ({{ lengthDiff(item.duration_diff) }})
                    </template>
                  </span>
                </span>
              </span>
              <a
                :href="item.url"
                target="_blank"
                rel="noopener"
                class="flex size-8 shrink-0 items-center justify-center rounded-control text-muted hover:bg-raised hover:text-fg"
                :title="t('replace.open')"
                :aria-label="t('replace.open')"
                @click.stop
              >
                <AppIcon name="arrow-up-right" :size="16" />
              </a>
            </div>
          </li>
        </ul>
      </template>
    </div>

    <template #footer>
      <UiButton variant="ghost" @click="close">
        {{ job ? t('common.close') : t('common.cancel') }}
      </UiButton>
      <UiButton
        v-if="!job"
        variant="primary"
        icon="retry"
        :loading="starting"
        :disabled="!chosen"
        @click="replace"
      >
        {{ t('replace.confirm') }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
// "Replace audio" (admins): search YouTube Music and YouTube for the right
// version of a library track - or paste a link - and swap the file's audio
// for it. The file keeps its name, tags, cover and lyrics, so it stays in
// its playlists. Opened from a track's menu (model/replaceAudio.js).
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiModal from '../ui/UiModal.vue'
import UiProgress from '../ui/UiProgress.vue'
import API from '/src/model/api'
import { useLibrary } from '/src/model/library'
import { useReplaceAudio } from '/src/model/replaceAudio'
import { useUi } from '/src/model/ui'
import { formatDuration } from '/src/lib/format'
import { lengthDiff, sameLength } from '/src/lib/replaceAudio'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const ui = useUi()
const library = useLibrary()
const { track, close: closeDialog } = useReplaceAudio()

const query = ref('')
const candidates = ref([])
const chosen = ref('')
const loading = ref(false)
const searched = ref(false)
const error = ref('')
const starting = ref(false)
const job = ref(null)
const serverLength = ref(0)

const length = computed(() => serverLength.value || track.value?.duration || 0)

function errorOf(err) {
  return err?.response?.data?.detail || t('toast.actionFailed')
}

async function load(text = '') {
  if (!track.value) return
  loading.value = true
  error.value = ''
  chosen.value = ''
  try {
    const { data } = await API.getReplaceCandidates(track.value.file, text)
    query.value = data.query
    candidates.value = data.candidates
    serverLength.value = data.track?.duration || 0
  } catch (err) {
    candidates.value = []
    error.value = errorOf(err)
  } finally {
    loading.value = false
    searched.value = true
  }
}

function search() {
  load(query.value.trim())
}

async function replace() {
  if (!chosen.value || !track.value) return
  starting.value = true
  error.value = ''
  try {
    const { data } = await API.replaceAudio(track.value.file, chosen.value)
    job.value = {
      id: data.job_id,
      status: 'downloading',
      progress: 0,
      message: '',
    }
  } catch (err) {
    error.value = errorOf(err)
  } finally {
    starting.value = false
  }
}

// Follow the job through the queue's progress messages.
const offMessage = API.onMessage((data) => {
  if (!job.value || data?.song?.song_id !== job.value.id) return
  job.value = {
    ...job.value,
    status: data.status,
    progress: Number(data.progress) || 0,
    message: data.status === 'done' ? '' : data.message || '',
  }
  if (data.status === 'done') {
    ui.toast(t('replace.done'), { kind: 'success' })
    library.load()
  }
})
onBeforeUnmount(() => offMessage?.())

function reset() {
  query.value = ''
  candidates.value = []
  chosen.value = ''
  searched.value = false
  error.value = ''
  job.value = null
  serverLength.value = 0
}

function close() {
  closeDialog()
}

watch(
  () => track.value?.file,
  (file) => {
    reset()
    if (file) load()
  }
)
</script>
