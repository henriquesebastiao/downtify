// The music trash (downtify/library_trash.py): what the server can do,
// and the pure helpers its page and the delete actions share.
import { ref } from 'vue'
import API from '/src/model/api'

/** The error codes the trash API answers with (`detail.code`). */
const ERROR_CODES = new Set([
  'admin_required',
  'admin_access_revoked',
  'atomic_move_unsupported',
  'confirmation_expired',
  'confirmation_invalid',
  'file_changed',
  'file_changed_during_move',
  'file_missing',
  'filesystem_unavailable',
  'identity_uncertain',
  'invalid_path',
  'invalid_selection',
  'item_not_found',
  'library_task_active',
  'nas_marker_changed',
  'nas_marker_missing',
  'operation_already_pending',
  'operation_in_progress',
  'operation_not_complete',
  'preview_busy',
  'preview_unavailable',
  'restore_collision',
  'retention_expired',
  'root_unavailable',
  'track_is_playing',
  'trash_file_changed',
  'trash_file_missing',
  'trash_ignore_invalid',
  'trash_not_configured',
  'trash_permissions_unsafe',
  'unsafe_symlink',
  'unsupported_collection',
  'unsupported_lyrics_location',
])

/** The i18n key for an error code, `trash.errors.unavailable` if unknown. */
export function trashErrorKey(code) {
  return 'trash.errors.' + (ERROR_CODES.has(code) ? code : 'unavailable')
}

/** The message for a failed trash request (an axios error). */
export function trashError(error, t) {
  return t(trashErrorKey(error?.response?.data?.detail?.code))
}

/** Operation states, as the server names them, and how each is shown. */
export const STATE_TONES = {
  pending: 'neutral',
  moving: 'neutral',
  trashed: 'accent',
  restore_pending: 'neutral',
  restoring: 'neutral',
  restored: 'neutral',
  purging: 'neutral',
  purged: 'neutral',
  error: 'danger',
}

/** Whether `item` can still be restored: in the trash (or stopped by an
 * error, files kept) and inside its retention. */
export function restorable(item, now = Date.now()) {
  if (!['trashed', 'error', 'pending'].includes(item?.state)) return false
  return !item.expires_at || item.expires_at * 1000 > now
}

/** One line per file for the confirmation, at most `max` of them (the
 * server takes 200 at once, so by default every one). */
export function previewLines(items, max = 200) {
  const lines = items.slice(0, max).map((item) => {
    const meta = item.metadata || {}
    const format = String(meta.codec || item.file.split('.').pop() || '')
    const title = meta.title
      ? [meta.artist, meta.title].filter(Boolean).join(' — ')
      : item.file
    return `• ${title} (${format.toUpperCase()})`
  })
  return { lines, more: Math.max(0, items.length - max) }
}

const enabled = ref(false)
const canManage = ref(false)
const retentionDays = ref(30)
let refreshed = 0
let loading = null

/** Ask the server again, at most every 30 s. An older server (404) or
 * one without the trash leaves everything off. */
async function refreshCapability() {
  if (loading) return loading
  if (Date.now() - refreshed < 30000) return
  loading = (async () => {
    try {
      const { data } = await API.trashCapabilities()
      enabled.value = Boolean(data.enabled)
      canManage.value = Boolean(data.can_manage)
      retentionDays.value = Number(data.retention_days) || 30
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
  return { enabled, canManage, retentionDays, refresh: refreshCapability }
}
