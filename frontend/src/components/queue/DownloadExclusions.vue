<template>
  <details
    v-if="auth.isAdmin.value"
    class="rounded-panel border border-line-2 p-4"
    @toggle="load"
  >
    <summary class="cursor-pointer font-semibold">
      {{ t('downloadPolicy.exclusions') }}
    </summary>
    <p v-if="error" role="alert" class="mt-3 text-danger">{{ error }}</p>
    <p v-if="loaded && !items.length" class="mt-3 text-muted">
      {{ t('downloadPolicy.empty') }}
    </p>
    <ul class="mt-3 flex flex-col gap-3">
      <li
        v-for="item in items"
        :key="item.id"
        class="flex items-center justify-between gap-3"
      >
        <div class="min-w-0">
          <div>{{ item.title }} · {{ item.artist }}</div>
          <small class="text-muted">{{
            t(`downloadPolicy.${item.reason}`)
          }}</small>
        </div>
        <UiButton
          size="sm"
          variant="secondary"
          :disabled="busy"
          @click="resume(item.id)"
          >{{ t('downloadPolicy.resume') }}</UiButton
        >
      </li>
    </ul>
  </details>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { useI18n } from '/src/i18n'
import UiButton from '/src/components/ui/UiButton.vue'

const auth = useAuth(),
  { t } = useI18n()
const items = ref([]),
  error = ref(''),
  loaded = ref(false),
  busy = ref(false)
async function load() {
  if (!auth.isAdmin.value) return
  try {
    items.value = (await API.downloadExclusions()).data.items
    error.value = ''
    loaded.value = true
  } catch {
    error.value = t('downloadPolicy.error')
  }
}
async function resume(id) {
  busy.value = true
  try {
    await API.resumeDownload(id)
    await load()
  } catch {
    error.value = t('downloadPolicy.error')
  } finally {
    busy.value = false
  }
}
onMounted(() =>
  window.addEventListener('downtify-download-policy-changed', load)
)
onUnmounted(() =>
  window.removeEventListener('downtify-download-policy-changed', load)
)
</script>
