<template>
  <div class="flex flex-col gap-3 px-5 py-4">
    <div class="flex flex-wrap items-center gap-2">
      <UiButton
        variant="primary"
        :disabled="busy"
        @click="ratings.start(false)"
      >
        {{ t('settings.ratingsRun') }}
      </UiButton>
      <UiButton :disabled="busy" @click="ratings.start(true)">
        {{ t('settings.ratingsPreview') }}
      </UiButton>
      <UiButton v-if="view.running" variant="ghost" @click="ratings.stop">
        {{ t('settings.ratingsStop') }}
      </UiButton>
    </div>

    <div v-if="view.running" class="flex flex-col gap-2">
      <p class="text-[13px] text-fg-3">{{ view.progressText }}</p>
      <UiProgress :value="view.percent" :indeterminate="view.indeterminate" />
    </div>

    <p v-if="ratings.runError.value" class="text-[13px] text-danger">
      {{ ratings.runError.value }}
    </p>
    <p v-if="view.lastError" class="text-[13px] text-danger">
      {{ view.lastError }}
    </p>
    <p v-else class="text-[13px] text-fg-3">{{ view.lastText }}</p>
    <p v-if="view.nextText" class="text-[13px] text-muted">
      {{ view.nextText }}
    </p>

    <div
      v-if="view.changes.length"
      class="overflow-hidden rounded-control border border-line-2"
    >
      <table class="w-full text-left text-[13px]">
        <thead class="bg-surface-2 text-muted">
          <tr>
            <th class="px-3 py-2 font-semibold">
              {{ t('settings.ratingsColSong') }}
            </th>
            <th class="px-2 py-2 text-right font-semibold whitespace-nowrap">
              {{ t('settings.ratingsColRank') }}
            </th>
            <th class="px-2 py-2 text-right font-semibold whitespace-nowrap">
              {{ t('settings.ratingsColStars') }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line">
          <tr v-for="(row, i) in view.changes" :key="i">
            <td class="px-3 py-2 break-words">
              <span class="block text-fg">{{ row.title }}</span>
              <span class="block text-muted">{{ row.artist }}</span>
            </td>
            <td class="tabular px-2 py-2 text-right whitespace-nowrap">
              {{ Number(row.rank).toLocaleString() }}
            </td>
            <td class="tabular px-2 py-2 text-right whitespace-nowrap">
              {{ row.was }} → {{ row.stars }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="view.changesTruncated" class="text-[13px] text-muted">
      {{ t('settings.ratingsFirstRows', { count: view.changes.length }) }}
    </p>

    <details v-if="view.unmatched.length" class="text-[13px]">
      <summary class="cursor-pointer text-fg-3">
        {{ t('settings.ratingsUnmatched', { count: view.unmatchedCount }) }}
      </summary>
      <ul class="mt-2 flex max-h-72 flex-col gap-1 overflow-y-auto text-muted">
        <li v-for="(line, i) in view.unmatched" :key="i" class="break-words">
          {{ line }}
        </li>
      </ul>
    </details>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted } from 'vue'

import { useI18n } from '/src/i18n'
import { useNavidromeRatings } from '/src/lib/navidromeRatings'
import UiButton from '/src/components/ui/UiButton.vue'
import UiProgress from '/src/components/ui/UiProgress.vue'

// The options are the settings page's, edited there: this only reads
// them when a run starts.
const props = defineProps({
  options: { type: Object, required: true },
})

const { t } = useI18n()
const ratings = useNavidromeRatings(() => props.options)
const view = ratings.view
const busy = computed(() => view.value.running || ratings.starting.value)

onMounted(ratings.refresh)
onBeforeUnmount(ratings.dispose)
</script>
