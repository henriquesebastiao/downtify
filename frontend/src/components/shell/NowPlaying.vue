<template>
  <Teleport to="body">
    <Transition name="now-playing">
      <div
        v-if="nowPlaying.isOpen.value && track"
        class="fixed inset-0 z-50 flex flex-col overflow-hidden bg-[#07080b] text-white"
        role="dialog"
        aria-modal="true"
        :aria-label="t('player.nowPlaying')"
      >
        <!-- Backdrop: the artwork, blown up and blurred. -->
        <div class="pointer-events-none absolute inset-0" aria-hidden="true">
          <div
            class="absolute inset-0 transition-colors duration-700"
            :style="{ backgroundColor: tint }"
          />
          <img
            v-if="track.hasCover"
            :src="track.cover"
            alt=""
            class="absolute inset-0 size-full scale-125 object-cover opacity-55 blur-[90px] saturate-150"
          />
          <div
            class="absolute inset-0 bg-gradient-to-b from-black/25 via-black/45 to-black/80"
          />
        </div>

        <div
          class="relative flex h-full flex-col px-5 pt-[max(1rem,env(safe-area-inset-top))] pb-[max(1.25rem,env(safe-area-inset-bottom))] lg:px-10 lg:pt-6 lg:pb-8"
        >
          <!-- Header -->
          <header class="flex h-12 shrink-0 items-center gap-3">
            <button
              ref="closeButton"
              type="button"
              class="flex size-10 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20"
              :aria-label="t('player.closeNowPlaying')"
              @click="nowPlaying.close()"
            >
              <AppIcon name="chevron-down" :size="22" />
            </button>
            <component
              :is="contextRoute ? RouterLink : 'div'"
              :to="contextRoute || undefined"
              class="flex min-w-0 flex-col max-lg:flex-1 max-lg:items-center"
              @click="contextRoute && nowPlaying.close()"
            >
              <span class="eyebrow !text-white/55">{{ contextLabel }}</span>
              <span class="max-w-full truncate text-sm font-semibold">{{
                contextTitle
              }}</span>
            </component>
            <div
              class="ml-auto hidden gap-1 rounded-[12px] bg-white/8 p-1 lg:flex"
              role="tablist"
            >
              <button
                v-for="tab in panels"
                :key="tab.id"
                type="button"
                role="tab"
                :aria-selected="panel === tab.id"
                class="flex h-9 items-center gap-2 rounded-[9px] px-3.5 text-[13px] transition-colors"
                :class="
                  panel === tab.id
                    ? 'bg-white/15 font-semibold text-white'
                    : 'font-medium text-white/65 hover:text-white'
                "
                @click="setPanel(tab.id)"
              >
                <AppIcon :name="tab.icon" :size="16" />{{ tab.label }}
              </button>
            </div>
            <UiMenu
              :items="trackMenu"
              :label="t('common.more')"
              class="lg:hidden"
            >
              <template #trigger>
                <button
                  type="button"
                  class="flex size-10 items-center justify-center rounded-full hover:bg-white/10"
                  :aria-label="t('common.more')"
                >
                  <AppIcon name="more" :size="22" />
                </button>
              </template>
            </UiMenu>
          </header>

          <!-- Body -->
          <div
            class="grid min-h-0 flex-1 gap-6 py-4 lg:grid-cols-[minmax(0,min(460px,38vw))_minmax(0,1fr)] lg:items-center lg:gap-14 lg:py-6 xl:grid-cols-[minmax(0,min(460px,32vw))_minmax(0,1fr)_340px]"
          >
            <!-- Artwork + title (hidden on phones while a panel is open) -->
            <div
              class="flex min-h-0 flex-col justify-center gap-6"
              :class="mobilePanel ? 'max-lg:hidden' : ''"
            >
              <div class="mx-auto w-full max-w-[min(100%,52vh)] lg:max-w-none">
                <CoverArt
                  :src="track.hasCover ? track.cover : ''"
                  :name="track.album || track.title"
                  rounded="rounded-[20px]"
                  :letter-size="140"
                  :icon-size="72"
                  class="aspect-square w-full shadow-[0_40px_100px_rgba(0,0,0,0.55)] transition-transform duration-500 ease-out-soft"
                  :class="player.isPlaying.value ? 'scale-100' : 'scale-[0.94]'"
                />
              </div>
              <div class="flex items-end justify-between gap-4">
                <div class="min-w-0">
                  <h2
                    class="text-display truncate text-2xl font-bold lg:text-[32px]"
                  >
                    {{ track.title }}
                  </h2>
                  <RouterLink
                    v-if="track.albumArtist"
                    :to="{ name: 'Artist', query: { name: track.albumArtist } }"
                    class="mt-1 block truncate text-base text-white/70 hover:text-white hover:underline"
                    @click="nowPlaying.close()"
                    >{{ track.artist }}</RouterLink
                  >
                  <p v-else class="mt-1 truncate text-base text-white/70">
                    {{ track.artist }}
                  </p>
                </div>
                <UiMenu
                  :items="trackMenu"
                  :label="t('common.more')"
                  class="hidden lg:inline-flex"
                >
                  <template #trigger>
                    <button
                      type="button"
                      class="flex size-10 items-center justify-center rounded-full hover:bg-white/10"
                      :aria-label="t('common.more')"
                    >
                      <AppIcon name="more" :size="22" />
                    </button>
                  </template>
                </UiMenu>
              </div>
              <p
                v-if="player.playError.value"
                class="flex items-center gap-2 text-sm text-danger"
              >
                <AppIcon name="alert" :size="16" />{{ t('player.cannotPlay') }}
              </p>
            </div>

            <!-- Main panel -->
            <div
              class="min-h-0 lg:h-full"
              :class="mobilePanel ? '' : 'max-lg:hidden'"
            >
              <LyricsPanel v-if="panel === 'lyrics'" :compact="isMobile" />
              <UpNextPanel v-else-if="panel === 'queue'" />
              <TrackDetails v-else-if="panel === 'details'" class="lg:pt-10" />
              <EqualizerPanel
                v-else-if="panel === 'equalizer'"
                :palette="palette"
              />
            </div>

            <!-- Up next always visible on wide screens -->
            <aside
              v-if="panel !== 'queue'"
              class="hidden h-full max-h-[620px] min-h-0 rounded-panel border border-white/10 bg-white/6 p-3 backdrop-blur-xl xl:block"
            >
              <UpNextPanel />
            </aside>
          </div>

          <!-- Transport -->
          <footer class="shrink-0">
            <div class="flex items-center gap-3">
              <span class="tabular w-12 text-xs text-white/65">{{
                formatDuration(scrub ?? player.currentTime.value)
              }}</span>
              <WaveSeekBar
                class="flex-1"
                :model-value="scrub ?? player.currentTime.value"
                :max="player.duration.value || 1"
                :label="t('player.seek')"
                :value-text="formatDuration(player.currentTime.value)"
                :playing="player.isPlaying.value"
                :palette="palette"
                @update:model-value="(v) => (scrub = v)"
                @commit="commitSeek"
              />
              <span class="tabular w-12 text-right text-xs text-white/65">{{
                formatDuration(player.duration.value)
              }}</span>
            </div>

            <div class="mt-3 flex items-center lg:mt-4">
              <div class="hidden flex-1 items-center gap-2 lg:flex">
                <span
                  v-if="track.format"
                  class="rounded-md border border-white/20 px-1.5 py-0.5 text-[11px] font-semibold tracking-wide text-white/75"
                  >{{ track.format }}</span
                >
                <span v-if="track.size" class="text-xs text-white/55">
                  {{ formatBytes(track.size) }}
                </span>
              </div>

              <div
                class="flex flex-1 items-center justify-between lg:flex-none lg:justify-center lg:gap-7"
              >
                <button
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full transition-colors hover:bg-white/10"
                  :class="
                    player.shuffle.value ? 'text-accent' : 'text-white/80'
                  "
                  :aria-label="t('player.shuffle')"
                  :aria-pressed="player.shuffle.value"
                  @click="player.toggleShuffle()"
                >
                  <AppIcon name="shuffle" :size="22" />
                </button>
                <button
                  type="button"
                  class="flex size-13 items-center justify-center rounded-full hover:bg-white/10"
                  :aria-label="t('player.previous')"
                  @click="player.prev()"
                >
                  <AppIcon name="prev" :size="28" />
                </button>
                <button
                  type="button"
                  class="flex size-[72px] items-center justify-center rounded-full bg-white text-[#0b0c0e] shadow-[0_12px_30px_rgba(0,0,0,0.35)] transition-transform hover:scale-105 active:scale-95"
                  :aria-label="
                    player.isPlaying.value
                      ? t('player.pause')
                      : t('player.play')
                  "
                  @click="player.toggle()"
                >
                  <AppIcon
                    :name="player.isPlaying.value ? 'pause' : 'play'"
                    :size="26"
                  />
                </button>
                <button
                  type="button"
                  class="flex size-13 items-center justify-center rounded-full hover:bg-white/10"
                  :aria-label="t('player.next')"
                  @click="player.next()"
                >
                  <AppIcon name="next" :size="28" />
                </button>
                <button
                  type="button"
                  class="relative flex size-11 items-center justify-center rounded-full transition-colors hover:bg-white/10"
                  :class="
                    player.repeatMode.value !== 'off'
                      ? 'text-accent'
                      : 'text-white/80'
                  "
                  :aria-label="repeatLabel"
                  @click="player.cycleRepeat()"
                >
                  <AppIcon
                    :name="
                      player.repeatMode.value === 'one'
                        ? 'repeat-one'
                        : 'repeat'
                    "
                    :size="22"
                  />
                </button>
              </div>

              <div class="hidden flex-1 items-center justify-end gap-2 lg:flex">
                <UiMenu :items="sleepMenu" :label="t('player.sleepTimer')">
                  <template #trigger>
                    <button
                      type="button"
                      class="flex h-10 items-center gap-2 rounded-full px-3 text-xs font-semibold transition-colors hover:bg-white/10"
                      :class="
                        player.sleepAt.value ? 'text-accent' : 'text-white/75'
                      "
                      :aria-label="t('player.sleepTimer')"
                    >
                      <AppIcon name="timer" :size="20" />
                      <span v-if="sleepLabel" class="tabular">{{
                        sleepLabel
                      }}</span>
                    </button>
                  </template>
                </UiMenu>
                <VolumeControl
                  width="w-28"
                  track-class="bg-white/20"
                  fill-class="bg-white"
                  thumb-class="bg-white"
                  class="text-white [&_button]:text-white/80 [&_button:hover]:bg-white/10"
                />
              </div>
            </div>

            <!-- Phone extras -->
            <div class="mt-4 flex items-center justify-between lg:hidden">
              <UiMenu
                :items="sleepMenu"
                :label="t('player.sleepTimer')"
                align="start"
              >
                <template #trigger>
                  <button
                    type="button"
                    class="flex h-10 items-center gap-2 rounded-full px-3 text-xs font-semibold"
                    :class="
                      player.sleepAt.value ? 'text-accent' : 'text-white/75'
                    "
                    :aria-label="t('player.sleepTimer')"
                  >
                    <AppIcon name="timer" :size="20" />
                    <span v-if="sleepLabel" class="tabular">{{
                      sleepLabel
                    }}</span>
                  </button>
                </template>
              </UiMenu>
              <div class="flex gap-2">
                <button
                  v-for="tab in panels"
                  :key="tab.id"
                  type="button"
                  class="flex h-10 items-center gap-2 rounded-full px-3.5 text-[13px] font-semibold transition-colors"
                  :class="
                    panel === tab.id && mobilePanel
                      ? 'bg-white text-[#0b0c0e]'
                      : 'bg-white/12 text-white'
                  "
                  :aria-pressed="panel === tab.id && mobilePanel"
                  @click="toggleMobilePanel(tab.id)"
                >
                  <AppIcon :name="tab.icon" :size="16" />
                  <span class="max-xs:sr-only">{{ tab.label }}</span>
                </button>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useMediaQuery, useNow } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiMenu from '../ui/UiMenu.vue'
import WaveSeekBar from '../player/WaveSeekBar.vue'
import VolumeControl from '../player/VolumeControl.vue'
import LyricsPanel from '../player/LyricsPanel.vue'
import UpNextPanel from '../player/UpNextPanel.vue'
import TrackDetails from '../player/TrackDetails.vue'
import EqualizerPanel from '../player/EqualizerPanel.vue'
import { usePlayer } from '/src/model/player'
import { useNowPlaying } from '/src/model/ui'
import { formatBytes, formatDuration, hueFor } from '/src/lib/format'
import { useCoverPalette } from '/src/model/coverPalette'
import { saveName } from '/src/lib/paths'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const nowPlaying = useNowPlaying()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const isMobile = useMediaQuery('(max-width: 1023px)')
const now = useNow({ interval: 15000 })
const scrub = ref(null)
const closeButton = ref(null)

const track = computed(() => player.currentTrack.value)
const palette = useCoverPalette(track)
const tint = computed(
  () =>
    palette.value?.background ||
    `oklch(0.3 0.06 ${hueFor(track.value?.album || track.value?.title)})`
)

const panels = computed(() => [
  { id: 'lyrics', icon: 'lyrics', label: t('player.lyrics') },
  { id: 'queue', icon: 'queue', label: t('player.upNext') },
  { id: 'details', icon: 'info', label: t('player.details') },
  { id: 'equalizer', icon: 'equalizer', label: t('player.equalizer') },
])

// ?panel= picks the side panel; phones show it instead of the artwork.
const panel = computed(() => {
  const requested = String(route.query.panel || '')
  if (panels.value.some((tab) => tab.id === requested)) return requested
  return 'lyrics'
})
const mobilePanel = computed(() => isMobile.value && !!route.query.panel)

function setPanel(id) {
  router.replace({ query: { ...route.query, panel: id } })
}

function toggleMobilePanel(id) {
  if (mobilePanel.value && panel.value === id) {
    const { panel: _panel, ...query } = route.query
    router.replace({ query })
  } else {
    setPanel(id)
  }
}

const context = computed(() => player.context.value)
const contextLabel = computed(() => {
  const type = context.value?.type
  return type ? t(`player.playingFrom.${type}`) : t('player.nowPlaying')
})
const contextTitle = computed(
  () => context.value?.title || track.value?.album || t('player.queue')
)
const contextRoute = computed(() => context.value?.route || null)

const repeatLabel = computed(
  () =>
    ({
      off: t('player.repeatOff'),
      all: t('player.repeatAll'),
      one: t('player.repeatOne'),
    })[player.repeatMode.value]
)

const sleepLabel = computed(() => {
  const at = player.sleepAt.value
  if (!at) return ''
  if (at === 'track') return t('player.sleepEndOfTrackShort')
  const minutes = Math.max(1, Math.ceil((at - now.value.getTime()) / 60000))
  return t('player.minutesLeft', { count: minutes })
})

const sleepMenu = computed(() => [
  { heading: t('player.sleepTimer') },
  ...[15, 30, 45, 60, 90].map((minutes) => ({
    label: t('player.sleepMinutes', { count: minutes }),
    action: () => player.setSleepTimer(minutes),
  })),
  {
    label: t('player.sleepEndOfTrack'),
    checked: player.sleepAt.value === 'track',
    action: () => player.setSleepTimer('track'),
  },
  { divider: true, hidden: !player.sleepAt.value },
  {
    label: t('player.sleepOff'),
    icon: 'x',
    hidden: !player.sleepAt.value,
    action: () => player.setSleepTimer(null),
  },
])

const trackMenu = computed(() => {
  const tr = track.value
  if (!tr) return []
  return [
    {
      label: t('player.goToAlbum'),
      icon: 'disc',
      hidden: !tr.album,
      action: () =>
        navigate({
          name: 'Album',
          query: { artist: tr.albumArtist, title: tr.album },
        }),
    },
    {
      label: t('player.goToArtist'),
      icon: 'user',
      hidden: !tr.albumArtist,
      action: () =>
        navigate({ name: 'Artist', query: { name: tr.albumArtist } }),
    },
    {
      label: t('library.saveToDevice'),
      icon: 'download',
      action: () => saveFile(tr),
    },
    { divider: true },
    {
      label: t('player.details'),
      icon: 'info',
      action: () =>
        isMobile.value ? toggleMobilePanel('details') : setPanel('details'),
    },
  ]
})

function navigate(to) {
  // Leave the overlay first so the new page isn't opened "under" it.
  router.replace({ query: {} }).then(() => router.push(to))
}

function saveFile(tr) {
  const a = document.createElement('a')
  a.href = tr.url
  a.download = saveName(tr.file)
  document.body.appendChild(a)
  a.click()
  a.remove()
}

function commitSeek(value) {
  player.seek(value)
  scrub.value = null
}

// Nothing to show once the queue empties.
watch(track, (value) => {
  if (!value && nowPlaying.isOpen.value) nowPlaying.close()
})

watch(
  () => nowPlaying.isOpen.value,
  async (open) => {
    document.documentElement.style.overflow = open ? 'hidden' : ''
    if (open) {
      await nextTick()
      closeButton.value?.focus()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  document.documentElement.style.overflow = ''
})
</script>
