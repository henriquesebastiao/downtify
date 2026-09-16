<template>
  <header
    class="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur-xl supports-[backdrop-filter]:bg-bg/70"
  >
    <div
      class="mx-auto flex h-16 max-w-[1680px] items-center gap-2 px-4 sm:gap-3 sm:px-6 md:h-[72px] lg:px-10"
    >
      <RouterLink
        :to="{ name: 'Home' }"
        class="md:hidden"
        :title="t('nav.home')"
      >
        <AppLogo :size="30" />
      </RouterLink>
      <div class="hidden items-center gap-1 md:flex">
        <UiIconButton
          icon="chevron-left"
          :label="t('nav.back')"
          size="sm"
          :disabled="!canGoBack"
          @click="router.back()"
        />
        <UiIconButton
          icon="chevron-right"
          :label="t('nav.forward')"
          size="sm"
          :disabled="!canGoForward"
          @click="router.forward()"
        />
      </div>
      <GlobalSearch class="min-w-0 flex-1 md:max-w-xl" />
      <div class="ml-auto hidden items-center gap-1 sm:flex">
        <UiIconButton
          icon="keyboard"
          :label="t('shortcuts.title')"
          class="hidden lg:inline-flex"
          @click="openShortcuts"
        />
        <UiIconButton
          :icon="theme.resolved.value === 'dark' ? 'sun' : 'moon'"
          :label="
            theme.resolved.value === 'dark'
              ? t('settings.themeLight')
              : t('settings.themeDark')
          "
          @click="theme.toggle()"
        />
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLogo from '../ui/AppLogo.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import GlobalSearch from './GlobalSearch.vue'
import { useTheme } from '/src/model/theme'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const theme = useTheme()

// vue-router records where history can go in history.state.
const canGoBack = computed(() => {
  route.fullPath
  return !!window.history.state?.back
})
const canGoForward = computed(() => {
  route.fullPath
  return !!window.history.state?.forward
})

function openShortcuts() {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: '?' }))
}
</script>
