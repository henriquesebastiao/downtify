<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-side/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl"
    :aria-label="t('nav.main')"
  >
    <div class="flex h-[4.75rem] items-stretch px-1 pt-1.5">
      <RouterLink
        v-for="item in items"
        :key="item.name"
        :to="{ name: item.name }"
        class="relative flex flex-1 flex-col items-center gap-1 pt-1.5"
        :class="isActive(item) ? 'text-fg' : 'text-faint'"
      >
        <AppIcon
          :name="item.icon"
          :size="22"
          :class="isActive(item) ? 'text-accent' : ''"
        />
        <span
          class="text-[10px]"
          :class="isActive(item) ? 'font-semibold' : 'font-medium'"
        >
          {{ t(item.label) }}
        </span>
        <span
          v-if="item.name === 'Queue' && pending"
          class="tabular absolute top-0 left-[calc(50%+4px)] flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-bold text-on-accent"
          >{{ pending }}</span
        >
      </RouterLink>
      <button
        type="button"
        class="relative flex flex-1 flex-col items-center gap-1 pt-1.5"
        :class="moreActive ? 'text-fg' : 'text-faint'"
        @click="sheet = true"
      >
        <AppIcon
          name="more"
          :size="22"
          :class="moreActive ? 'text-accent' : ''"
        />
        <span
          class="text-[10px]"
          :class="moreActive ? 'font-semibold' : 'font-medium'"
        >
          {{ t('nav.more') }}
        </span>
        <span
          v-if="hasUpdate"
          class="absolute top-1 left-[calc(50%+6px)] size-2 rounded-full bg-accent"
        />
      </button>
    </div>

    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="sheet"
          class="fixed inset-0 z-[70] flex items-end bg-black/50 md:hidden"
          @click.self="sheet = false"
        >
          <div
            class="w-full animate-rise rounded-t-[22px] border-t border-line-3 bg-surface px-4 pt-3 pb-[calc(1rem+env(safe-area-inset-bottom))]"
          >
            <div class="mx-auto mb-3 h-1 w-10 rounded-full bg-line-3" />
            <a
              v-if="hasUpdate"
              :href="update.release_url"
              target="_blank"
              rel="noopener"
              class="mb-1 flex h-14 items-center gap-4 rounded-control px-2 text-[15px] font-semibold text-accent"
            >
              <span
                class="flex size-9 items-center justify-center rounded-[10px] bg-accent/12"
              >
                <AppIcon name="sparkle" :size="18" />
              </span>
              {{ t('nav.updateAvailable', { version: update.latest_version }) }}
              <AppIcon name="arrow-up-right" :size="16" class="ml-auto" />
            </a>
            <RouterLink
              v-for="link in moreLinks"
              :key="link.name"
              :to="{ name: link.name }"
              class="flex h-14 items-center gap-4 rounded-control px-2 text-[15px] font-medium"
              @click="sheet = false"
            >
              <span
                class="flex size-9 items-center justify-center rounded-[10px] bg-surface-2 text-fg-3"
              >
                <AppIcon :name="link.icon" :size="18" />
              </span>
              {{ t(link.label) }}
              <AppIcon
                name="chevron-right"
                :size="18"
                class="ml-auto text-faint"
              />
            </RouterLink>
            <button
              type="button"
              class="flex h-14 w-full items-center gap-4 rounded-control px-2 text-[15px] font-medium"
              @click="theme.toggle()"
            >
              <span
                class="flex size-9 items-center justify-center rounded-[10px] bg-surface-2 text-fg-3"
              >
                <AppIcon
                  :name="theme.resolved.value === 'dark' ? 'sun' : 'moon'"
                  :size="18"
                />
              </span>
              {{
                theme.resolved.value === 'dark'
                  ? t('settings.themeLight')
                  : t('settings.themeDark')
              }}
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </nav>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import { useI18n } from '/src/i18n'
import { useTheme } from '/src/model/theme'
import { useUpdateCheck } from '/src/model/updateCheck'
import { usePendingCount } from './navState'

const { t } = useI18n()
const route = useRoute()
const theme = useTheme()
const pending = usePendingCount()
const sheet = ref(false)
const update = useUpdateCheck().status
const hasUpdate = computed(() => Boolean(update.value?.update_available))

const items = [
  { name: 'Home', icon: 'home', label: 'nav.home' },
  { name: 'Search', icon: 'search', label: 'nav.search', match: ['Link'] },
  {
    name: 'Library',
    icon: 'library',
    label: 'nav.library',
    match: ['Album', 'Artist', 'Playlist'],
  },
  { name: 'Queue', icon: 'download', label: 'nav.queue' },
]
const moreLinks = [
  { name: 'Monitor', icon: 'radar', label: 'nav.monitor' },
  { name: 'Settings', icon: 'settings', label: 'nav.settings' },
]

function isActive(item) {
  return route.name === item.name || (item.match || []).includes(route.name)
}

const moreActive = computed(() =>
  moreLinks.some((link) => link.name === route.name)
)

watch(
  () => route.fullPath,
  () => (sheet.value = false)
)
</script>
