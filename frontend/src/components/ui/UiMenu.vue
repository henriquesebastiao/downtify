<template>
  <span ref="triggerEl" class="inline-flex" @click.stop="toggle">
    <slot name="trigger" :open="open">
      <UiIconButton :icon="icon" :label="label" :size="size" />
    </slot>
  </span>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        ref="menuEl"
        role="menu"
        class="fixed z-[70] min-w-52 max-w-72 overflow-hidden rounded-[12px] border border-line-3 bg-surface py-1.5 shadow-float"
        :style="position"
        @keydown="onKeydown"
      >
        <template v-for="(item, i) in visibleItems" :key="i">
          <div v-if="item.divider" class="my-1.5 h-px bg-line" />
          <p v-else-if="item.heading" class="eyebrow px-3.5 pt-2 pb-1">
            {{ item.heading }}
          </p>
          <button
            v-else
            type="button"
            role="menuitem"
            :disabled="item.disabled"
            class="flex h-10 w-full items-center gap-3 px-3.5 text-left text-sm transition-colors focus:outline-none disabled:opacity-40"
            :class="
              item.danger
                ? 'text-danger hover:bg-danger/10 focus:bg-danger/10'
                : 'text-fg-2 hover:bg-surface-2 focus:bg-surface-2'
            "
            @click="run(item)"
          >
            <AppIcon v-if="item.icon" :name="item.icon" :size="17" />
            <span class="min-w-0 flex-1 truncate">{{ item.label }}</span>
            <AppIcon
              v-if="item.checked"
              name="check"
              :size="16"
              class="text-accent"
            />
          </button>
        </template>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import UiIconButton from './UiIconButton.vue'

const props = defineProps({
  items: { type: Array, required: true },
  label: { type: String, default: 'More' },
  icon: { type: String, default: 'more' },
  size: { type: String, default: 'md' },
  align: { type: String, default: 'end' },
})

const open = ref(false)
const triggerEl = ref(null)
const menuEl = ref(null)
const anchor = ref({ x: 0, y: 0, width: 0, height: 0, point: false })
const position = ref({})

const visibleItems = computed(() => props.items.filter((item) => !item.hidden))

function place() {
  const menu = menuEl.value
  if (!menu) return
  const { innerWidth: vw, innerHeight: vh } = window
  const w = menu.offsetWidth
  const h = menu.offsetHeight
  const a = anchor.value
  let left = a.point || props.align === 'start' ? a.x : a.x + a.width - w
  let top = a.y + a.height + 6
  if (top + h > vh - 8) top = Math.max(8, a.y - h - 6)
  left = Math.min(Math.max(8, left), vw - w - 8)
  position.value = { left: `${left}px`, top: `${top}px` }
}

async function show(nextAnchor) {
  anchor.value = nextAnchor
  position.value = { left: '-9999px', top: '0px' }
  open.value = true
  await nextTick()
  place()
  menuEl.value?.querySelector('button:not(:disabled)')?.focus()
  document.addEventListener('pointerdown', onOutside, true)
  window.addEventListener('resize', hide)
  window.addEventListener('scroll', hide, true)
}

function hide() {
  open.value = false
  document.removeEventListener('pointerdown', onOutside, true)
  window.removeEventListener('resize', hide)
  window.removeEventListener('scroll', hide, true)
}

function toggle() {
  if (open.value) {
    hide()
    return
  }
  const rect = triggerEl.value.getBoundingClientRect()
  show({
    x: rect.left,
    y: rect.top,
    width: rect.width,
    height: rect.height,
    point: false,
  })
}

/** Open at the pointer, for right-click context menus. */
function openAt(event) {
  event.preventDefault()
  show({ x: event.clientX, y: event.clientY, width: 0, height: 0, point: true })
}

function onOutside(event) {
  if (menuEl.value?.contains(event.target)) return
  if (triggerEl.value?.contains(event.target)) return
  hide()
}

function run(item) {
  hide()
  item.action?.()
}

function onKeydown(event) {
  const buttons = [...menuEl.value.querySelectorAll('button:not(:disabled)')]
  const index = buttons.indexOf(document.activeElement)
  if (event.key === 'Escape') {
    hide()
    triggerEl.value?.querySelector('button')?.focus()
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    buttons[(index + 1) % buttons.length]?.focus()
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    buttons[(index - 1 + buttons.length) % buttons.length]?.focus()
  } else if (event.key === 'Tab') {
    hide()
  }
}

onBeforeUnmount(hide)

defineExpose({ openAt, hide })
</script>
