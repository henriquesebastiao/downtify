<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="flex items-center justify-between gap-3 px-2 pb-3">
      <div class="min-w-0">
        <p class="text-sm font-semibold text-white">{{ t('player.upNext') }}</p>
        <p class="truncate text-xs text-white/55">
          {{ summary }}
        </p>
      </div>
      <button
        v-if="upcoming.length && !player.dj.value"
        type="button"
        class="shrink-0 rounded-control px-2.5 py-1.5 text-xs font-semibold text-white/70 hover:bg-white/10 hover:text-white"
        @click="player.clearUpcoming()"
      >
        {{ t('player.clearUpcoming') }}
      </button>
    </div>
    <div v-if="djController.available.value" class="mx-2 mb-3">
      <button
        type="button"
        class="rounded-full border border-white/20 px-3 py-2 text-sm font-semibold hover:bg-white/10 disabled:opacity-50"
        :aria-pressed="Boolean(player.dj.value || djController.busy.value)"
        :disabled="
          !player.dj.value &&
          !djController.busy.value &&
          !djController.ready.value
        "
        @click="
          player.dj.value || djController.busy.value
            ? djController.stop()
            : djController.startQueue()
        "
      >
        {{
          player.dj.value || djController.busy.value
            ? 'Désactiver le mode DJ'
            : 'Mode DJ'
        }}
      </button>
      <p class="mt-2 text-xs text-white/60" role="status">
        {{
          djController.notice.value ||
          (!djController.ready.value
            ? 'Disponible après validation du moteur sur ce serveur.'
            : 'Transitions adaptées · ordre de la file conservé')
        }}
      </p>
      <p
        v-if="
          djController.proof.value && musicAI.capabilities.value?.administrator
        "
        class="mt-2 text-xs text-white/60"
        role="status"
      >
        Validation :
        {{ Math.floor(djController.proof.value.continuous_seconds / 60) }} min
        continues ·
        {{ djController.proof.value.total_interruptions || 0 }} interruption(s).
      </p>
    </div>
    <div
      v-if="player.dj.value && djController.failure.value"
      class="mx-2 mb-3"
      role="alert"
    >
      <p class="text-sm text-red-300">{{ djController.failure.value }}</p>
      <button
        type="button"
        class="mt-2 rounded-full border border-white/20 px-3 py-2 text-sm"
        @click="djController.stop()"
      >
        Retour classique
      </button>
    </div>
    <div
      v-if="player.dj.value?.transition !== null && player.dj.value"
      class="mx-2 mb-3 rounded-lg bg-white/10 p-3"
      role="status"
    >
      <span class="text-xs font-semibold">Transition en cours</span>
      <progress
        class="mt-2 h-1 w-full accent-violet-400 motion-reduce:transition-none"
        :value="player.dj.value.transition"
        max="1"
        aria-label="Transition vers le prochain titre"
      />
    </div>

    <div
      class="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1 [scrollbar-width:thin]"
    >
      <div
        v-if="current"
        class="mb-1 flex h-14 items-center gap-3 rounded-[10px] bg-white/10 px-2.5"
      >
        <CoverArt
          :thumb="150"
          :src="current.hasCover ? current.cover : ''"
          :name="current.album || current.title"
          rounded="rounded-[6px]"
          :letter-size="12"
          :icon-size="14"
          class="size-10"
        />
        <div class="min-w-0 flex-1">
          <p class="flex items-center gap-1.5">
            <span class="truncate text-sm font-semibold text-accent">{{
              current.title
            }}</span>
            <ExplicitBadge v-if="current.explicit" tone="onDark" />
          </p>
          <p class="truncate text-xs text-white/55">{{ current.artist }}</p>
        </div>
        <EqBars :size="12" :playing="player.isPlaying.value" />
      </div>

      <TransitionGroup name="list" tag="ol">
        <li
          v-for="(item, position) in upcoming"
          :key="`${item.track.file}-${item.index}`"
          class="group flex h-14 items-center gap-3 rounded-[10px] px-2.5 transition-colors hover:bg-white/8"
          :class="dragOver === position ? 'bg-white/12' : ''"
          :draggable="!player.shuffle.value && !player.dj.value"
          @dragstart="onDragStart($event, item.index)"
          @dragover.prevent="dragOver = position"
          @dragleave="dragOver = -1"
          @drop.prevent="onDrop(item.index)"
          @dragend="dragOver = -1"
        >
          <button
            type="button"
            class="flex min-w-0 flex-1 items-center gap-3 text-left"
            :disabled="Boolean(player.dj.value)"
            @click="player.playAt(item.index)"
          >
            <CoverArt
              :thumb="150"
              :src="item.track.hasCover ? item.track.cover : ''"
              :name="item.track.album || item.track.title"
              rounded="rounded-[6px]"
              :letter-size="12"
              :icon-size="14"
              class="size-10"
            />
            <span class="min-w-0 flex-1">
              <span class="flex items-center gap-1.5">
                <span class="truncate text-sm font-medium text-white">{{
                  item.track.title
                }}</span>
                <ExplicitBadge v-if="item.track.explicit" tone="onDark" />
              </span>
              <span class="block truncate text-xs text-white/55">{{
                item.track.artist
              }}</span>
            </span>
          </button>
          <span class="tabular text-xs text-white/45 group-hover:hidden">
            {{ item.track.duration ? formatDuration(item.track.duration) : '' }}
          </span>
          <button
            v-if="!player.dj.value"
            type="button"
            class="hidden size-8 items-center justify-center rounded-full text-white/60 hover:bg-white/10 hover:text-white group-hover:flex"
            :aria-label="t('player.removeFromQueue')"
            @click="player.removeAt(item.index)"
          >
            <AppIcon name="x" :size="16" />
          </button>
          <AppIcon
            v-if="!player.shuffle.value && !player.dj.value"
            name="grip"
            :size="16"
            class="hidden cursor-grab text-white/35 sm:block"
          />
        </li>
      </TransitionGroup>

      <p
        v-if="!upcoming.length"
        class="px-2 py-8 text-center text-sm text-white/50"
      >
        {{ t('player.queueEnds') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import ExplicitBadge from '../ui/ExplicitBadge.vue'
import { usePlayer } from '/src/model/player'
import { djController } from '/src/model/djController'
import { musicAI } from '/src/model/musicAI'
import { formatDuration, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const { t } = useI18n()
const dragOver = ref(-1)
let dragFrom = -1

const current = computed(() => player.currentTrack.value)
// Long queues render the first stretch only; the rest is still queued.
const upcoming = computed(() => player.upcoming.value.slice(0, 200))

const summary = computed(() => {
  const rest = player.upcoming.value
  const length = splitLength(
    rest.reduce((sum, item) => sum + (item.track.duration || 0), 0)
  )
  const parts = [t('common.tracks', { count: rest.length })]
  if (length.hours || length.minutes) {
    parts.push(
      length.hours
        ? t('common.lengthHours', length)
        : t('common.lengthMinutes', length)
    )
  }
  return parts.join(' · ')
})

function onDragStart(event, index) {
  dragFrom = index
  event.dataTransfer.effectAllowed = 'move'
}

function onDrop(index) {
  if (dragFrom >= 0 && dragFrom !== index) player.moveTrack(dragFrom, index)
  dragFrom = -1
  dragOver.value = -1
}
</script>
