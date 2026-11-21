<template>
  <UiModal
    :open="whatsNew.open.value"
    :title="t('whatsNew.title', { version: whatsNew.version.value })"
    @close="whatsNew.close"
  >
    <template v-if="whatsNew.highlights.value.length">
      <p class="text-sm text-pretty text-fg-2">
        {{ t('whatsNew.intro', { version: whatsNew.version.value }) }}
      </p>
      <ul class="mt-4 space-y-3">
        <li
          v-for="(line, i) in whatsNew.highlights.value"
          :key="i"
          class="flex gap-3 text-sm text-pretty text-fg"
        >
          <span
            class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-accent/15 text-accent"
          >
            <AppIcon name="sparkle" :size="12" stroke-width="2.2" />
          </span>
          <span>{{ line }}</span>
        </li>
      </ul>
    </template>
    <p v-else class="text-sm text-pretty text-fg-2">
      {{ t('whatsNew.noHighlights', { version: whatsNew.version.value }) }}
    </p>
    <!-- A gentle nudge, not a button: easy to read past. -->
    <a
      :href="REPO_URL"
      target="_blank"
      rel="noopener"
      class="mt-5 inline-flex items-center gap-1.5 text-[13px] text-muted transition-colors hover:text-fg"
    >
      <AppIcon name="star" :size="14" stroke-width="2" />
      {{ t('whatsNew.star') }}
    </a>
    <template #footer>
      <UiButton
        variant="ghost"
        icon="arrow-up-right"
        :href="whatsNew.url.value"
      >
        {{ t('whatsNew.changelog') }}
      </UiButton>
      <UiButton variant="primary" @click="whatsNew.close">
        {{ t('whatsNew.gotIt') }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
// The first visit after an update: the release's highlights, a link to
// its full changelog on GitHub, and a quiet "star the repo" line.
import { watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import UiModal from '../ui/UiModal.vue'
import { REPO_URL } from '/src/lib/whatsNew'
import { useAuth } from '/src/model/auth'
import { useDefaultPasswordPrompt } from '/src/model/defaultPassword'
import { useWhatsNew } from '/src/model/whatsNew'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const auth = useAuth()
const whatsNew = useWhatsNew()

// Once someone is signed in (or nobody has to), and after the "change
// the default password" prompt, so the two never stack.
const passwordPrompt = useDefaultPasswordPrompt()
watch(
  () => [auth.loaded.value, auth.mustSignIn.value, passwordPrompt.open.value],
  ([loaded, mustSignIn, passwordPromptOpen]) => {
    if (!loaded || mustSignIn || passwordPromptOpen) return
    whatsNew.check()
  },
  { immediate: true }
)
</script>
