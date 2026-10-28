import { ref } from 'vue'
import API from '/src/model/api'

const codes = new Set([
  'admin_required',
  'trash_not_configured',
  'file_changed',
  'file_missing',
  'filesystem_unavailable',
  'nas_marker_missing',
  'nas_marker_changed',
  'root_unavailable',
  'unsupported_collection',
  'confirmation_expired',
  'confirmation_invalid',
  'restore_collision',
  'trash_file_changed',
  'trash_file_missing',
  'retention_expired',
  'admin_access_revoked',
  'track_is_playing',
  'invalid_selection',
  'item_not_found',
  'operation_already_pending',
  'operation_not_complete',
  'unsafe_symlink',
  'invalid_path',
  'trash_permissions_unsafe',
  'atomic_move_unsupported',
  'file_changed_during_move',
  'identity_uncertain',
  'preview_busy',
  'preview_unavailable',
  'library_task_active',
  'trash_ignore_invalid',
  'unsupported_lyrics_location',
  'operation_in_progress',
])
export function trashError(error, t) {
  const code = error?.response?.data?.detail?.code
  return t('trash.errors.' + (codes.has(code) ? code : 'unavailable'))
}

const enabled = ref(false)
const canManage = ref(false)
let refreshed = 0
let loading = null
async function refreshCapability() {
  if (loading) return loading
  if (Date.now() - refreshed < 30000) return
  loading = (async () => {
    try {
      const { data } = await API.trashCapabilities()
      enabled.value = Boolean(data.enabled)
      canManage.value = Boolean(data.can_manage)
    } catch {
      enabled.value = false
      canManage.value = false
    } finally {
      refreshed = Date.now()
      loading = null
    }
  })()
  return loading
}
export function useTrashCapability() {
  refreshCapability()
  return { enabled, canManage, refresh: refreshCapability }
}
