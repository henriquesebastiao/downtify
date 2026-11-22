<template>
  <DoctorSection
    id="formats"
    :title="t('doctor.formatsTitle')"
    :description="t('doctor.formatsHint')"
    :status="badge.text"
    :status-tone="badge.tone"
    :stale="stale && Boolean(found)"
    :busy="busy"
    @recheck="scan"
  >
    <SettingRow
      :label="t('doctor.formatsPick')"
      :description="t('doctor.formatsPickHint')"
      stacked
    >
      <div class="flex flex-col gap-3">
        <FormatPicker
          v-model="chosen"
          :disabled="busy"
          :label="t('doctor.formatsPick')"
        />
        <div>
          <UiButton
            icon="search"
            :loading="runningKind === 'formats'"
            :disabled="busy || !chosen.length"
            @click="scan"
          >
            {{ t('doctor.formatsFind') }}
          </UiButton>
        </div>
      </div>
    </SettingRow>

    <template v-if="found">
      <div class="flex flex-col gap-2 px-5 py-4 text-[13px]">
        <p v-if="!found.count" class="text-fg">
          {{ t('doctor.formatsNone', { formats: foundFormats }) }}
        </p>
        <template v-else>
          <p class="text-fg">
            {{
              t('doctor.formatsFound', {
                count: found.count,
                formats: foundFormats,
                size: formatBytes(found.bytes),
              })
            }}
          </p>
          <p class="text-muted">
            {{
              t('doctor.formatsEstimate', {
                bitrate: found.bitrate,
                size: formatBytes(found.estimated),
                saved: formatBytes(savedBytes(found.bytes, found.estimated)),
              })
            }}
          </p>
          <p class="text-muted">{{ t('doctor.formatsDuplicatesFirst') }}</p>
          <p v-if="!found.ffmpeg" class="text-danger">
            {{ t('doctor.error.convert_no_ffmpeg') }}
          </p>
        </template>
      </div>

      <ul
        v-if="found.count"
        class="flex flex-col gap-1.5 px-5 pb-4 text-[13px]"
        :aria-label="t('doctor.formatsListLabel')"
      >
        <li
          v-for="file in shownFiles"
          :key="file.file"
          class="flex flex-col rounded-control bg-surface-2 px-3 py-2"
        >
          <span class="truncate text-fg" :title="file.file">{{
            file.file
          }}</span>
          <span class="truncate text-muted">
            {{ formatLabel(file.format) }} · {{ formatBytes(file.size) }} →
            {{
              t('doctor.formatsAbout', { size: formatBytes(file.estimated) })
            }}
          </span>
        </li>
      </ul>
      <div v-if="found.count > shownFiles.length" class="px-5 pb-4">
        <UiButton variant="plain" size="sm" @click="shown += PAGE">
          {{ t('doctor.showMore') }}
        </UiButton>
      </div>

      <div v-if="found.count" class="flex flex-wrap gap-2 px-5 py-4">
        <UiButton
          variant="primary"
          icon="retry"
          :disabled="busy || stale || !found.ffmpeg"
          @click="convert"
        >
          {{
            t('doctor.formatsConvert', {
              count: found.count,
              bitrate: found.bitrate,
            })
          }}
        </UiButton>
      </div>
    </template>

    <div v-if="converted" class="flex flex-col gap-1 px-5 py-4 text-[13px]">
      <p class="text-fg">
        {{
          t('doctor.formatsConverted', {
            count: converted.converted.length,
            saved: formatBytes(
              savedBytes(converted.bytes_before, converted.bytes_after)
            ),
          })
        }}
      </p>
      <p v-if="converted.cancelled" class="text-muted">
        {{ t('doctor.formatsStopped', { count: converted.left }) }}
      </p>
      <p v-if="converted.converted.length" class="text-muted">
        {{
          converted.trash
            ? t('doctor.formatsInTrash')
            : t('doctor.formatsDeleted')
        }}
      </p>
      <template v-if="converted.failed.length">
        <p class="text-warn">
          {{ t('doctor.formatsFailed', { count: converted.failed.length }) }}
        </p>
        <ul class="flex flex-col gap-1">
          <li
            v-for="item in converted.failed.slice(0, 25)"
            :key="item.file"
            class="truncate text-muted"
            :title="item.file"
          >
            {{ item.file }} · {{ failure(item.error) }}
          </li>
        </ul>
      </template>
    </div>
  </DoctorSection>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

import { useI18n } from '/src/i18n'
import { useUi } from '/src/model/ui'
import { formatBytes } from '/src/lib/format'
import { formatLabel, savedBytes } from '/src/lib/audioFormats'
import UiButton from '/src/components/ui/UiButton.vue'
import SettingRow from '/src/components/settings/SettingRow.vue'
import FormatPicker from '/src/components/settings/FormatPicker.vue'
import DoctorSection from '/src/components/settings/doctor/DoctorSection.vue'

const props = defineProps({
  // The last format scan (doctor_routes._formats_found), or null.
  found: { type: Object, default: null },
  // The last conversion run (doctor_routes._convert_files), or null.
  converted: { type: Object, default: null },
  busy: { type: Boolean, default: false },
  runningKind: { type: String, default: '' },
  stale: { type: Boolean, default: false },
})
const emit = defineEmits(['scan', 'convert'])
const { t } = useI18n()
const ui = useUi()

const PAGE = 25
const shown = ref(PAGE)
const chosen = ref(['flac'])

watch(
  () => props.found,
  (found) => {
    shown.value = PAGE
    if (found?.formats?.length) chosen.value = [...found.formats]
  },
  { immediate: true }
)

const foundFormats = computed(() =>
  (props.found?.formats || []).map(formatLabel).join(', ')
)
const shownFiles = computed(() =>
  (props.found?.files || []).slice(0, shown.value)
)
const badge = computed(() => {
  const found = props.found
  if (!found) return { text: t('doctor.badge.notChecked'), tone: 'neutral' }
  if (!found.count) return { text: t('doctor.badge.allGood'), tone: 'accent' }
  return {
    text: t('doctor.badge.toConvert', {
      count: found.count,
      size: formatBytes(found.bytes),
    }),
    tone: 'warn',
  }
})

function failure(code) {
  const key = `doctor.convertError.${code}`
  const text = t(key)
  return text === key ? code : text
}

function scan() {
  if (!chosen.value.length) return
  emit('scan', chosen.value)
}

async function convert() {
  const found = props.found
  const ok = await ui.confirm({
    title: t('doctor.formatsConvertTitle'),
    body: t('doctor.formatsConvertBody', {
      count: found.count,
      bitrate: found.bitrate,
      where: found.trash ? t('doctor.dupeToTrash') : t('doctor.dupeForGood'),
    }),
    confirmLabel: t('doctor.formatsConvertConfirm'),
    danger: !found.trash,
  })
  if (!ok) return
  emit(
    'convert',
    found.files.map((f) => f.file)
  )
}
</script>
