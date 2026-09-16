<template>
  <div
    v-if="!loaded"
    class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-10 sm:px-6 md:flex-row md:items-end lg:px-10"
  >
    <UiSkeleton
      class="size-48 self-center !rounded-[16px] sm:size-56 md:self-auto"
    />
    <div class="flex flex-1 flex-col gap-3">
      <UiSkeleton class="h-3 w-24" />
      <UiSkeleton class="h-12 w-2/3" />
      <UiSkeleton class="h-4 w-1/2" />
    </div>
  </div>
  <div
    v-else-if="!found"
    class="mx-auto max-w-[1680px] px-4 pt-10 sm:px-6 lg:px-10"
  >
    <UiEmpty :icon="icon" :title="missing" :body="t('library.maybeDeleted')">
      <UiButton :to="{ name: 'Library' }" icon="library">{{
        t('library.backToLibrary')
      }}</UiButton>
    </UiEmpty>
  </div>
  <div v-else class="animate-rise">
    <slot />
  </div>
</template>

<script setup>
import UiButton from '../ui/UiButton.vue'
import UiEmpty from '../ui/UiEmpty.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import { useI18n } from '/src/i18n'

defineProps({
  loaded: { type: Boolean, default: false },
  found: { type: Boolean, default: false },
  icon: { type: String, default: 'music' },
  missing: { type: String, default: '' },
})
const { t } = useI18n()
</script>
