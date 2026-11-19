<template>
  <!-- A Spotify *user* link pasted where an artist (or playlist) link was
       meant: open.spotify.com/user/drake is a listener's account, not
       the artist's page (open.spotify.com/artist/...). It can't be
       watched, so this explains the difference before anything is
       added, and offers to look the artist up by name instead. -->
  <UiModal
    :open="!!userId"
    :title="t('monitor.userLinkTitle')"
    width="sm:max-w-xl"
    @close="$emit('back')"
  >
    <div class="flex flex-col gap-3 text-sm text-fg-3">
      <p>{{ t('monitor.userLinkBody') }}</p>
      <dl
        class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 rounded-control bg-surface-2 px-4 py-3 text-[13px]"
      >
        <dt class="font-semibold text-warn">
          {{ t('monitor.userLinkYours') }}
        </dt>
        <dd class="min-w-0 truncate font-mono text-fg">{{ link }}</dd>
        <dt class="font-semibold text-accent">
          {{ t('monitor.userLinkArtist') }}
        </dt>
        <dd class="min-w-0 truncate font-mono text-muted">
          open.spotify.com/artist/…
        </dd>
      </dl>
      <p class="text-muted">{{ t('monitor.userLinkHint') }}</p>
    </div>
    <template #footer>
      <UiButton variant="ghost" @click="$emit('back')">
        {{ t('monitor.userLinkBack') }}
      </UiButton>
      <UiButton variant="primary" icon="search" @click="$emit('search')">
        {{ t('monitor.userLinkSearch') }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
import { useI18n } from '/src/i18n'
import UiButton from '/src/components/ui/UiButton.vue'
import UiModal from '/src/components/ui/UiModal.vue'

defineProps({
  // The Spotify user id of the pasted link ('' = closed).
  userId: { type: String, default: '' },
  link: { type: String, default: '' },
})
defineEmits(['back', 'search'])

const { t } = useI18n()
</script>
