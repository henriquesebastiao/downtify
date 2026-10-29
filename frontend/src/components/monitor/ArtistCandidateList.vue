<template>
  <!-- YouTube Music artists that could be the one meant, each with its
       photo and profile link to tell namesakes apart. Used by the
       Monitor's artist suggestions and the Library artist page's Watch
       artist. -->
  <ul class="grid max-h-[60vh] gap-3 overflow-y-auto sm:grid-cols-2">
    <li
      v-for="candidate in candidates"
      :key="candidate.artist_id"
      class="rounded-xl border border-line-2 bg-surface-2 p-3"
    >
      <div class="flex items-center gap-3">
        <CoverArt
          :src="candidate.image_url || ''"
          :name="candidate.name"
          :alt="candidate.name"
          round
          icon="user"
          :letter-size="24"
          class="size-16 flex-none"
        />
        <div class="min-w-0">
          <p class="truncate font-semibold">{{ candidate.name }}</p>
          <a
            :href="candidate.url"
            target="_blank"
            rel="noopener noreferrer"
            class="mt-1 inline-block text-xs text-muted underline underline-offset-4"
            >{{ t('artistSuggestions.inspect') }}</a
          >
        </div>
      </div>
      <UiButton
        size="sm"
        variant="primary"
        class="mt-3 w-full"
        :disabled="busy"
        :loading="busy && chosen === candidate.url"
        @click="$emit('choose', candidate)"
      >
        {{ t('artistSuggestions.followProfile') }}
      </UiButton>
    </li>
  </ul>
</template>

<script setup>
import UiButton from '/src/components/ui/UiButton.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import { useI18n } from '/src/i18n'

defineProps({
  // `{ name, artist_id, url, image_url }` rows of
  // GET /api/monitor/artist-suggestions/resolve.
  candidates: { type: Array, required: true },
  // A watch is being added: every button waits.
  busy: { type: Boolean, default: false },
  // The link being followed, whose button spins.
  chosen: { type: String, default: '' },
})
defineEmits(['choose'])

const { t } = useI18n()
</script>
