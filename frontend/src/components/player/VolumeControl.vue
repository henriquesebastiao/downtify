<template>
  <div v-if="!compact" class="flex items-center gap-2">
    <UiIconButton
      :icon="icon"
      :label="player.isMuted.value ? t('player.unmute') : t('player.mute')"
      size="sm"
      @click="player.toggleMute()"
    />
    <SliderBar
      :model-value="player.isMuted.value ? 0 : player.volume.value * 100"
      :label="t('player.volume')"
      :value-text="`${Math.round(player.volume.value * 100)}%`"
      :step="5"
      :class="width"
      :track-class="trackClass"
      :fill-class="fillClass"
      :thumb-class="thumbClass"
      @update:model-value="(v) => player.setVolume(v / 100)"
    />
  </div>

  <!-- No room for the slider on the bar (issue #552): the button opens it
       above, with the mute switch, like a menu. -->
  <span v-else ref="trigger" class="inline-flex">
    <UiIconButton
      :icon="icon"
      :label="t('player.volume')"
      :active="open"
      toggle
      size="sm"
      aria-haspopup="dialog"
      :aria-expanded="open"
      @click="toggle"
    />
    <Teleport to="body">
      <Transition name="menu">
        <div
          v-if="open"
          ref="panel"
          role="dialog"
          :aria-label="t('player.volume')"
          class="fixed z-[70] flex items-center gap-2 rounded-[12px] border border-line-3 bg-surface py-1.5 pr-4 pl-1.5 shadow-float"
          :style="position"
          @keydown.esc.stop="close(true)"
        >
          <UiIconButton
            :icon="icon"
            :label="
              player.isMuted.value ? t('player.unmute') : t('player.mute')
            "
            size="sm"
            @click="player.toggleMute()"
          />
          <SliderBar
            :model-value="player.isMuted.value ? 0 : player.volume.value * 100"
            :label="t('player.volume')"
            :value-text="`${Math.round(player.volume.value * 100)}%`"
            :step="5"
            class="w-32"
            :track-class="trackClass"
            :fill-class="fillClass"
            :thumb-class="thumbClass"
            always-thumb
            @update:model-value="(v) => player.setVolume(v / 100)"
          />
        </div>
      </Transition>
    </Teleport>
  </span>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import SliderBar from './SliderBar.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { usePlayer } from '/src/model/player'
import { popoverOrigin } from '/src/lib/motion'
import { useI18n } from '/src/i18n'

const props = defineProps({
  width: { type: String, default: 'w-24' },
  trackClass: { type: String, default: 'bg-raised' },
  fillClass: { type: String, default: 'bg-fg-3 group-hover:bg-accent' },
  thumbClass: { type: String, default: 'bg-fg' },
  // Only a button; the slider opens in a popover.
  compact: { type: Boolean, default: false },
})

const player = usePlayer()
const { t } = useI18n()

const icon = computed(() => {
  if (player.isMuted.value || player.volume.value === 0) return 'volume-mute'
  return player.volume.value < 0.5 ? 'volume-low' : 'volume'
})

const open = ref(false)
const trigger = ref(null)
const panel = ref(null)
const position = ref({})

function place() {
  const button = trigger.value?.getBoundingClientRect()
  const box = panel.value
  if (!button || !box) return
  const { innerWidth: vw } = window
  const w = box.offsetWidth
  const h = box.offsetHeight
  // The player sits at the bottom of the page: open upwards.
  const top = Math.max(8, button.top - h - 8)
  const left = Math.min(
    Math.max(8, button.left + button.width / 2 - w / 2),
    vw - w - 8
  )
  position.value = {
    left: `${left}px`,
    top: `${top}px`,
    transformOrigin: popoverOrigin({ left, top, width: w, height: h }, button),
  }
}

async function show() {
  position.value = { left: '-9999px', top: '0px' }
  open.value = true
  await nextTick()
  place()
  panel.value?.querySelector('[role="slider"]')?.focus()
  document.addEventListener('pointerdown', onOutside, true)
  window.addEventListener('resize', close)
}

function close(refocus = false) {
  if (!open.value) return
  open.value = false
  document.removeEventListener('pointerdown', onOutside, true)
  window.removeEventListener('resize', close)
  if (refocus === true) trigger.value?.querySelector('button')?.focus()
}

function toggle() {
  if (open.value) close()
  else show()
}

function onOutside(event) {
  if (panel.value?.contains(event.target)) return
  if (trigger.value?.contains(event.target)) return
  close()
}

// The bar grew back: the inline slider takes over.
watch(
  () => props.compact,
  (compact) => {
    if (!compact) close()
  }
)

onBeforeUnmount(() => close())
</script>
