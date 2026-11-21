<template>
  <!-- What slskd's folder holds next to what Downtify counts: why the
       folder looks bigger in a file browser than on the storage page. -->
  <div class="flex flex-col gap-3 px-5 py-4 text-[13px]">
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <p class="font-semibold text-fg">{{ t('doctor.folder.title') }}</p>
      <p class="tabular text-muted">
        {{
          t('doctor.folder.total', {
            files: folder.total.files,
            size: formatBytes(folder.total.bytes),
          })
        }}
      </p>
    </div>
    <div
      v-if="folder.total.bytes"
      class="flex h-2 w-full overflow-hidden rounded-full bg-surface-2"
      aria-hidden="true"
    >
      <span
        v-for="row in rows"
        :key="row.kind"
        :class="row.bar"
        :style="{ width: `${(row.bytes / folder.total.bytes) * 100}%` }"
      />
    </div>
    <ul class="flex flex-col gap-1.5">
      <li
        v-for="row in rows"
        :key="row.kind"
        class="flex items-start gap-3 rounded-control bg-surface-2 px-3 py-2"
      >
        <span class="mt-1 size-2.5 shrink-0 rounded-full" :class="row.bar" />
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="text-fg">{{ t(`doctor.folder.${row.kind}`) }}</span>
          <span class="text-pretty text-muted">
            {{ t(`doctor.folder.${row.kind}Hint`) }}
          </span>
        </span>
        <span class="tabular shrink-0 text-right text-muted">
          {{ formatBytes(row.bytes) }}<br />
          {{ t('doctor.folder.files', { count: row.files }) }}
        </span>
      </li>
    </ul>
    <p v-if="folder.other_by_extension.length" class="text-muted">
      {{ t('doctor.folder.otherKinds') }}
      <span
        v-for="ext in folder.other_by_extension"
        :key="ext.extension"
        class="tabular mr-2 inline-block"
      >
        .{{ ext.extension || '?' }} {{ formatBytes(ext.bytes) }}
      </span>
    </p>
    <details
      v-for="kind in listedKinds"
      :key="kind"
      class="rounded-control bg-surface-2 px-3 py-2"
    >
      <summary class="cursor-pointer text-fg">
        {{ t(`doctor.folder.${kind}List`) }}
      </summary>
      <ul class="mt-2 flex flex-col gap-1">
        <li
          v-for="file in folder.examples[kind]"
          :key="file.file"
          class="flex items-center gap-2"
        >
          <span class="min-w-0 flex-1 truncate text-muted">{{
            file.file
          }}</span>
          <span class="tabular shrink-0 text-muted">{{
            formatBytes(file.bytes)
          }}</span>
        </li>
      </ul>
    </details>
    <p class="text-faint">{{ t('doctor.folder.units') }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { useI18n } from '/src/i18n'
import { formatBytes } from '/src/lib/format'

const props = defineProps({
  // `health.slskd.folder` (doctor.slskd_folder_breakdown).
  folder: { type: Object, required: true },
})

const { t } = useI18n()

const BARS = {
  library: 'bg-accent',
  leftover: 'bg-warn',
  unlisted_audio: 'bg-danger',
  other: 'bg-fg-3',
}

const rows = computed(() =>
  Object.keys(BARS).map((kind) => ({
    kind,
    bar: BARS[kind],
    ...(props.folder.kinds?.[kind] || { files: 0, bytes: 0 }),
  }))
)

const listedKinds = computed(() =>
  ['unlisted_audio', 'other'].filter(
    (kind) => props.folder.examples?.[kind]?.length
  )
)
</script>
