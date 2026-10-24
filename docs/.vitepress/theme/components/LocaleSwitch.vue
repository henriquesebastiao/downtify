<template>
  <div ref="root" class="relative">
    <button
      type="button"
      class="flex h-10 items-center gap-1.5 rounded-control border border-line-2 px-2.5 text-xs font-semibold text-muted transition-colors hover:border-line-3 hover:text-fg"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-label="ui.changeLanguage"
      :title="ui.changeLanguage"
      @click="toggle"
      @keydown.esc="close"
    >
      <Icon name="globe" :size="16" />
      <span class="hidden sm:inline">{{ current.name }}</span>
      <span class="sm:hidden">{{ current.code }}</span>
    </button>
    <Transition name="fade">
      <ul
        v-if="open"
        role="listbox"
        :aria-label="ui.language"
        class="absolute right-0 z-40 mt-2 max-h-[min(70vh,420px)] w-52 overflow-y-auto rounded-panel border border-line-3 bg-surface p-1.5 shadow-float"
        @keydown.esc="close"
      >
        <li
          v-for="item in locales"
          :key="item.code"
          role="option"
          :aria-selected="item.code === current.code"
        >
          <a
            :href="hrefFor(item)"
            :hreflang="item.code"
            :lang="item.lang"
            class="flex h-9 items-center gap-2.5 rounded-control px-2.5 text-sm transition-colors"
            :class="
              item.code === current.code
                ? 'bg-surface-2 font-semibold text-fg'
                : 'text-muted hover:bg-surface-2/60 hover:text-fg'
            "
            @click="pick(item, $event)"
          >
            <span class="min-w-0 flex-1 truncate">{{ item.name }}</span>
            <Icon
              v-if="item.code === current.code"
              name="check"
              :size="15"
              class="text-accent"
            />
          </a>
        </li>
      </ul>
    </Transition>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vitepress'
import Icon from './Icon.vue'
import { useLocale } from '../composables/locale'
import { useUi } from '../composables/ui'

const { ui } = useUi()
const { locales, current, hrefFor, remember } = useLocale()
const router = useRouter()
const open = ref(false)
const root = ref(null)

function toggle() {
  open.value = !open.value
}
function close() {
  open.value = false
}

function pick(item, event) {
  remember(item)
  close()
  // The same page in the other language, keeping the section being read.
  if (item.code !== current.value.code) {
    event.preventDefault()
    router.go(hrefFor(item) + location.hash)
  }
}

function onPointer(event) {
  if (open.value && !root.value?.contains(event.target)) close()
}

onMounted(() => document.addEventListener('pointerdown', onPointer))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onPointer))
</script>
