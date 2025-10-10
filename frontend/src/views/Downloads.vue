<template>
  <div class="min-h-screen">
    <Navbar />
    <div class="container mx-auto p-4">
      <h1 class="text-2xl mb-4">Downloads</h1>
      <div class="mb-4 flex items-center space-x-2">
        <button
          class="btn btn-primary btn-sm"
          @click="refresh"
          :disabled="loading"
        >
          <span
            v-if="loading"
            class="loading loading-spinner loading-xs"
          ></span>
          <span v-else>Refresh</span>
        </button>
      </div>
      <div v-if="error" class="alert alert-error mb-4">{{ error }}</div>
      <div class="card bg-base-100 shadow">
        <div class="card-body">
          <ul class="space-y-2">
            <li
              v-for="file in files"
              :key="file"
              class="flex items-center justify-between"
            >
              <span class="truncate mr-2">{{ file }}</span>
              <div class="flex items-center space-x-2">
                <a
                  class="btn btn-sm"
                  :href="`/downloads/${encodeURIComponent(file)}`"
                  download
                  >Download</a
                >
                <button
                  class="btn btn-sm btn-error"
                  @click="onDelete(file)"
                  :disabled="deleting[file] === true"
                >
                  <span
                    v-if="deleting[file] === true"
                    class="loading loading-spinner loading-xs"
                  ></span>
                  <span v-else>Delete</span>
                </button>
              </div>
            </li>
          </ul>
          <div v-if="!loading && files.length === 0" class="text-sm opacity-70">
            No files found.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Navbar from '/src/components/Navbar.vue'
import API from '/src/model/api'

const files = ref([])
const loading = ref(false)
const error = ref('')
const deleting = ref({})

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const res = await API.listDownloads()
    files.value = res.data || []
  } catch (e) {
    error.value = 'Failed to load downloads'
  } finally {
    loading.value = false
  }
}

async function onDelete(file) {
  deleting.value = { ...deleting.value, [file]: true }
  try {
    await API.deleteDownload(file)
    files.value = files.value.filter((f) => f !== file)
  } catch (e) {
    alert('Failed to delete ' + file)
  } finally {
    deleting.value = { ...deleting.value, [file]: false }
  }
}

onMounted(() => {
  refresh()
})
</script>

<style scoped></style>
