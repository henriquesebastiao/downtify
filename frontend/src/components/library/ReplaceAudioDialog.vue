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

      <!-- Replaced by hand before: downloads leave the file alone. -->
      <div
        v-if="handReplaced"
        class="flex flex-col gap-1.5 rounded-control bg-accent/8 px-3 py-2 text-[13px]"
      >
        <span class="flex items-start gap-2">
          <AppIcon name="lock" :size="15" class="mt-0.5 shrink-0 text-accent" />
          <span class="min-w-0 flex-1">
            {{ t('replace.handReplaced', { date: replacedOn }) }}
          </span>
        </span>
        <UiButton
          class="self-start"
          size="sm"
          variant="ghost"
          icon="unlock"
          :loading="lifting"
          @click="forget"
        >
          {{ t('replace.unprotect') }}
        </UiButton>
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
                  : job.status === 'uploading'
                    ? t('replace.uploading')
                    : t('replace.running')
            }}
          </p>
          <UiProgress
            v-if="job.status === 'downloading' || job.status === 'uploading'"
            :value="job.progress"
            :indeterminate="!job.progress || job.progress >= 100"
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
              @click="pick(item.video_id)"
              @keydown.enter.prevent="pick(item.video_id)"
              @keydown.space.prevent="pick(item.video_id)"
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

        <!-- Or the right audio from the admin's own device. -->
        <div class="flex flex-col gap-2 border-t border-line-2 pt-3">
          <p class="text-sm font-semibold">{{ t('replace.fileTitle') }}</p>
          <p class="text-[13px] text-muted">
            {{ t('replace.fileHint', { format: ownFormat }) }}
          </p>
          <input
            ref="picker"
            type="file"
            class="hidden"
            :accept="ACCEPT"
            @change="picked"
          />
          <div
            v-if="upload"
            role="radio"
            tabindex="0"
            :aria-checked="useFile"
            class="flex cursor-pointer items-center gap-3 rounded-control border px-2.5 py-2 transition-colors"
            :class="
              useFile
                ? 'border-accent bg-accent/8'
                : 'border-transparent hover:bg-surface-2'
            "
            @click="chooseFile"
            @keydown.enter.prevent="chooseFile"
            @keydown.space.prevent="chooseFile"
          >
            <span
              class="flex h-11 w-[4.5rem] shrink-0 items-center justify-center rounded-[6px] bg-surface-2 text-muted"
            >
              <AppIcon name="file-music" :size="20" />
            </span>
            <span class="flex min-w-0 flex-1 flex-col">
              <span class="text-sm font-medium [overflow-wrap:anywhere]">
                {{ upload.name }}
              </span>
              <span class="text-[12px] text-muted">
                {{ formatBytes(upload.size) }} ·
                {{ extension(upload.name).toUpperCase() }}
                <template v-if="needsConversion">→ {{ ownFormat }}</template>
              </span>
            </span>
          </div>
          <UiButton
            class="self-start"
            size="sm"
            variant="ghost"
            icon="upload"
            @click="picker?.click()"
          >
            {{ upload ? t('replace.fileOther') : t('replace.fileChoose') }}
          </UiButton>
        </div>
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
        :disabled="!(useFile ? upload : chosen)"
        @click="useFile ? replaceFromFile() : replace()"
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
import { formatBytes, formatDuration } from '/src/lib/format'
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
// A file from the admin's device instead of a found version.
const ACCEPT = 'audio/*,.mp3,.flac,.m4a,.ogg,.opus,.wav,.aiff,.aif,.aac,.webm'
const picker = ref(null)
const upload = ref(null)
const useFile = ref(false)
// Set when the audio was replaced by hand: downloads leave the file be.
const handReplaced = ref(null)
const lifting = ref(false)

const length = computed(() => serverLength.value || track.value?.duration || 0)
const extension = (name) => (name || '').split('.').pop().toLowerCase()
const ownFormat = computed(() => extension(track.value?.file).toUpperCase())
const needsConversion = computed(
  () =>
    Boolean(upload.value) &&
    extension(upload.value.name) !== extension(track.value?.file)
)
const replacedOn = computed(() =>
  handReplaced.value
    ? new Date(handReplaced.value.replaced_at * 1000).toLocaleDateString()
    : ''
)

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

async function loadHandReplaced() {
  const file = track.value?.file
  if (!file) return
  try {
    const { data } = await API.getHandReplaced(file)
    if (track.value?.file === file) handReplaced.value = data.hand_replaced
  } catch {
    handReplaced.value = null
  }
}

async function forget() {
  if (!track.value) return
  lifting.value = true
  try {
    await API.forgetHandReplaced(track.value.file)
    handReplaced.value = null
    ui.toast(t('replace.unprotected'), { kind: 'success' })
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    lifting.value = false
  }
}

function pick(videoId) {
  chosen.value = videoId
  useFile.value = false
}

function chooseFile() {
  useFile.value = true
  chosen.value = ''
}

function picked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  upload.value = file
  chooseFile()
}

async function replaceFromFile() {
  if (!upload.value || !track.value) return
  starting.value = true
  error.value = ''
  job.value = { status: 'uploading', progress: 0, message: '' }
  try {
    const { data } = await API.replaceAudioFromFile(
      track.value.file,
      upload.value,
      (share) => {
        if (job.value) job.value = { ...job.value, progress: share * 100 }
      }
    )
    job.value = {
      status: 'done',
      progress: 100,
      message: data.converted
        ? t('replace.fileConverted', { format: ownFormat.value })
        : '',
    }
    handReplaced.value = data.hand_replaced
    ui.toast(t('replace.done'), { kind: 'success' })
    library.load()
  } catch (err) {
    job.value = { status: 'error', progress: 0, message: errorOf(err) }
  } finally {
    starting.value = false
  }
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

// Follow the job through the queue's progress messages (an upload isn't
// a queue job: it has no id, and its request says when it's done).
const offMessage = API.onMessage((data) => {
  if (!job.value?.id || data?.song?.song_id !== job.value.id) return
  job.value = {
    ...job.value,
    status: data.status,
    progress: Number(data.progress) || 0,
    message: data.status === 'done' ? '' : data.message || '',
  }
  if (data.status === 'done') {
    ui.toast(t('replace.done'), { kind: 'success' })
    library.load()
    loadHandReplaced()
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
  upload.value = null
  useFile.value = false
  handReplaced.value = null
}

function close() {
  closeDialog()
}

watch(
  () => track.value?.file,
  (file) => {
    reset()
    if (file) {
      load()
      loadHandReplaced()
    }
  }
)
</script>
