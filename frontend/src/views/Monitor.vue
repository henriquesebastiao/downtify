<template>
  <div class="min-h-screen">
    <Navbar />
    <div class="container mx-auto p-4">
      <h1 class="text-2xl mb-4">Playlist Monitoring</h1>
      <p class="mb-4 text-sm opacity-70">
        Monitor Spotify playlists for new tracks. When new songs are added to a
        monitored playlist, they will be automatically downloaded.
      </p>

      <!-- Add Playlist Form -->
      <div class="card bg-base-100 shadow mb-4">
        <div class="card-body">
          <h2 class="card-title text-lg">Add Playlist to Monitor</h2>
          <div class="flex items-center space-x-2">
            <input
              v-model="newPlaylistUrl"
              type="text"
              placeholder="https://open.spotify.com/playlist/..."
              class="input input-bordered flex-grow"
              @keyup.enter="addPlaylist"
              :disabled="adding"
            />
            <button
              class="btn btn-primary"
              @click="addPlaylist"
              :disabled="adding || !newPlaylistUrl.trim()"
            >
              <span
                v-if="adding"
                class="loading loading-spinner loading-xs"
              ></span>
              <span v-else>Add</span>
            </button>
          </div>
          <div v-if="addError" class="alert alert-error mt-2">
            {{ addError }}
          </div>
          <div v-if="addSuccess" class="alert alert-success mt-2">
            {{ addSuccess }}
          </div>
        </div>
      </div>

      <!-- Manual Check Button -->
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
        <button
          class="btn btn-secondary btn-sm"
          @click="manualCheck"
          :disabled="checking"
        >
          <span
            v-if="checking"
            class="loading loading-spinner loading-xs"
          ></span>
          <span v-else>Check Now</span>
        </button>
      </div>

      <div v-if="error" class="alert alert-error mb-4">{{ error }}</div>
      <div v-if="checkResult" class="alert alert-info mb-4">
        {{ checkResult }}
      </div>

      <!-- Monitored Playlists List -->
      <div class="card bg-base-100 shadow">
        <div class="card-body">
          <h2 class="card-title">Monitored Playlists</h2>
          <div
            v-if="loading && playlists.length === 0"
            class="text-center py-4"
          >
            <span class="loading loading-spinner loading-lg"></span>
          </div>
          <div v-else-if="playlists.length === 0" class="text-sm opacity-70">
            No playlists are being monitored. Add one above to get started.
          </div>
          <div v-else class="overflow-x-auto">
            <table class="table w-full">
              <thead>
                <tr>
                  <th>Playlist Name</th>
                  <th>Tracks</th>
                  <th>Added</th>
                  <th>Last Checked</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="playlist in playlists" :key="playlist.playlist_id">
                  <td>
                    <div class="font-medium">{{ playlist.name }}</div>
                    <div class="text-xs opacity-50 truncate max-w-xs">
                      {{ playlist.url }}
                    </div>
                  </td>
                  <td>{{ playlist.total_tracks }}</td>
                  <td>
                    <div class="text-xs">
                      {{ formatDate(playlist.added_at) }}
                    </div>
                  </td>
                  <td>
                    <div class="text-xs">
                      {{ formatDate(playlist.last_checked) || 'Never' }}
                    </div>
                  </td>
                  <td>
                    <button
                      class="btn btn-sm btn-error"
                      @click="removePlaylist(playlist.url)"
                      :disabled="removing[playlist.playlist_id] === true"
                    >
                      <span
                        v-if="removing[playlist.playlist_id] === true"
                        class="loading loading-spinner loading-xs"
                      ></span>
                      <span v-else>Remove</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
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

const playlists = ref([])
const loading = ref(false)
const error = ref('')
const removing = ref({})
const newPlaylistUrl = ref('')
const adding = ref(false)
const addError = ref('')
const addSuccess = ref('')
const checking = ref(false)
const checkResult = ref('')

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const res = await API.listMonitoredPlaylists()
    playlists.value = res.data || []
  } catch (e) {
    error.value = 'Failed to load monitored playlists'
  } finally {
    loading.value = false
  }
}

async function addPlaylist() {
  if (!newPlaylistUrl.value.trim()) return

  adding.value = true
  addError.value = ''
  addSuccess.value = ''

  try {
    const res = await API.addMonitoredPlaylist(newPlaylistUrl.value.trim())
    if (res.data.success) {
      addSuccess.value = `Added "${res.data.playlist_name}" with ${res.data.total_tracks} tracks`
      newPlaylistUrl.value = ''
      await refresh()
      // Clear success message after 5 seconds
      setTimeout(() => {
        addSuccess.value = ''
      }, 5000)
    } else {
      addError.value = res.data.message || 'Failed to add playlist'
    }
  } catch (e) {
    addError.value =
      'Failed to add playlist. Please check the URL and try again.'
  } finally {
    adding.value = false
  }
}

async function removePlaylist(playlistUrl) {
  const playlist = playlists.value.find((p) => p.url === playlistUrl)
  if (!playlist) return

  removing.value = { ...removing.value, [playlist.playlist_id]: true }
  try {
    const res = await API.removeMonitoredPlaylist(playlistUrl)
    if (res.data.success) {
      playlists.value = playlists.value.filter((p) => p.url !== playlistUrl)
    } else {
      alert(res.data.message || 'Failed to remove playlist')
    }
  } catch (e) {
    alert('Failed to remove playlist')
  } finally {
    removing.value = { ...removing.value, [playlist.playlist_id]: false }
  }
}

async function manualCheck() {
  checking.value = true
  checkResult.value = ''
  error.value = ''

  try {
    const res = await API.checkMonitoredPlaylists()
    if (res.data.success) {
      const results = res.data.results
      checkResult.value = `Check complete: ${results.total_new_tracks} new tracks found, ${results.playlists_changed} playlists changed`
      await refresh()
      // Clear result message after 10 seconds
      setTimeout(() => {
        checkResult.value = ''
      }, 10000)
    } else {
      error.value = res.data.message || 'Failed to check playlists'
    }
  } catch (e) {
    error.value = 'Failed to check playlists'
  } finally {
    checking.value = false
  }
}

function formatDate(dateString) {
  if (!dateString) return null
  const date = new Date(dateString)
  return date.toLocaleString()
}

onMounted(() => {
  refresh()
})
</script>

<style scoped></style>
