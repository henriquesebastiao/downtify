<template>
  <section
    class="relative flex flex-1 items-center justify-center px-6 pt-24 pb-16 overflow-hidden"
  >
    <div aria-hidden="true" class="pointer-events-none absolute inset-0 -z-10">
      <div
        class="absolute left-1/2 top-1/4 -translate-x-1/2 h-[420px] w-[420px] rounded-full bg-primary/25 blur-[120px]"
      ></div>
      <div
        class="absolute right-10 bottom-12 h-64 w-64 rounded-full bg-primary/10 blur-3xl"
      ></div>
    </div>

    <div class="relative w-full max-w-2xl text-center animate-slide-up">
      <div class="mx-auto mb-6 inline-flex">
        <div
          class="relative inline-flex h-24 w-24 items-center justify-center rounded-3xl surface-strong shadow-glow"
        >
          <img src="../assets/downtify.svg" class="h-14 w-14" />
        </div>
      </div>

      <h1 class="text-balance text-5xl sm:text-6xl font-bold tracking-tight">
        Down<span class="text-primary">tify</span>
      </h1>
      <p
        class="mx-auto mt-5 max-w-md text-balance text-base sm:text-lg text-base-content/70"
      >
        {{ t('hero.tagline') }}
      </p>

      <div class="mt-10">
        <SearchInput class="w-full" />

        <div class="mt-5">
          <button
            type="button"
            class="inline-flex max-w-full items-center gap-1.5 text-xs text-base-content/50 hover:text-base-content/80 transition-colors"
            :disabled="importing"
            :title="t('hero.importCsv')"
            @click="triggerCsvPicker"
          >
            <span
              v-if="importing"
              class="loading loading-spinner loading-xs shrink-0"
            ></span>
            <Icon
              v-else
              icon="fa6-solid:file-import"
              class="h-3.5 w-3.5 shrink-0"
            />
            <span class="min-w-0 truncate">{{ t('hero.importCsv') }}</span>
          </button>
          <input
            ref="csvInput"
            type="file"
            accept=".csv,text/csv"
            class="hidden"
            @change="onCsvSelected"
          />
          <p v-if="importError" class="mt-2 text-xs text-error">
            {{ importError }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { Icon } from '@iconify/vue'
import SearchInput from './SearchInput.vue'
import router from '../router'
import { useDownloadManager } from '../model/download'
import { useI18n } from '../i18n'

const { t } = useI18n()

const dm = useDownloadManager()
const csvInput = ref(null)
const importing = ref(false)
const importError = ref('')

function triggerCsvPicker() {
  importError.value = ''
  csvInput.value?.click()
}

function onCsvSelected(event) {
  const file = event.target.files && event.target.files[0]
  event.target.value = ''
  if (!file) return

  importError.value = ''
  importing.value = true
  const playlistName = file.name.replace(/\.csv$/i, '')
  dm.fromCsvFile(file, playlistName)
    .then(() => {
      router.push({ name: 'Download' })
    })
    .catch((err) => {
      console.log('CSV import failed:', err.message)
      importError.value =
        err?.response?.data?.detail || t('hero.importCsvError')
    })
    .finally(() => {
      importing.value = false
    })
}
</script>
