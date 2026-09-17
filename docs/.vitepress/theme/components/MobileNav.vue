<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 bg-black/55 backdrop-blur-sm lg:hidden"
        @click="$emit('close')"
      />
    </Transition>
    <Transition name="drawer">
      <div
        v-if="open"
        id="mobile-nav"
        ref="panel"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        class="fixed inset-y-0 left-0 z-50 flex w-[min(320px,86vw)] flex-col border-r border-line-3 bg-side shadow-float lg:hidden"
        @keydown="onKeydown"
      >
        <div class="flex h-16 shrink-0 items-center gap-2.5 px-5">
          <Logo :size="26" />
          <span class="text-display text-[18px] font-bold">Downtify</span>
          <button
            ref="closeButton"
            type="button"
            class="-mr-2 ml-auto flex size-10 items-center justify-center rounded-control text-fg-3 hover:bg-surface-2"
            aria-label="Close navigation"
            @click="$emit('close')"
          >
            <Icon name="x" :size="20" />
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-3 pt-2 pb-6">
          <NavList />
        </div>
        <div
          class="flex shrink-0 items-center justify-between gap-2 border-t border-line px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]"
        >
          <ThemeSwitch />
          <SocialLinks />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import Icon from './Icon.vue'
import Logo from './Logo.vue'
import NavList from './NavList.vue'
import SocialLinks from './SocialLinks.vue'
import ThemeSwitch from './ThemeSwitch.vue'
import { trapTab } from '../focus'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['close'])
const panel = ref(null)
const closeButton = ref(null)

watch(
  () => props.open,
  async (open) => {
    document.documentElement.style.overflow = open ? 'hidden' : ''
    if (!open) return
    await nextTick()
    closeButton.value?.focus()
  }
)

function onKeydown(event) {
  if (event.key === 'Escape') emit('close')
  else trapTab(event, panel.value)
}
</script>
