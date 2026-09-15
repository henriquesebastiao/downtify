<template>
  <footer class="mt-auto px-6 py-6 text-center text-sm text-base-content/60">
    <div v-if="version" class="mb-2">
      <span class="badge-soft">v{{ version }}</span>
    </div>
    <a
      class="font-semibold text-primary hover:underline"
      href="https://github.com/henriquesebastiao/downtify"
      target="_blank"
      rel="noopener"
      >Downtify</a
    >
    <span class="mx-2 opacity-50">·</span>
    <span>{{ t('footer.tagline') }}</span>

    <div v-if="uc.status.value?.update_available" class="mt-3">
      <a
        :href="uc.status.value.release_url"
        target="_blank"
        rel="noopener"
        class="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary hover:bg-primary/15"
      >
        <Icon icon="fa6-solid:download" class="h-3.5 w-3.5" />
        {{
          t('footer.updateAvailable', {
            version: uc.status.value.latest_version,
          })
        }}
      </a>
    </div>
  </footer>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Icon } from '@iconify/vue'
import { useI18n } from '../i18n'
import { useUpdateCheck } from '../model/updateCheck'

const { t } = useI18n()
const uc = useUpdateCheck()

// Set by api.js's getVersion() (GET /api/version) once the app loads.
const version = ref(localStorage.getItem('version') || '')
onMounted(() => {
  const v = localStorage.getItem('version')
  if (v) version.value = v
})
</script>
