// The activity log's kinds (downtify/activity.py KINDS), as the admins'
// Activity page shows them. Pure, so they're unit-testable.

export const ACTIVITY_KINDS = [
  'login',
  'login_failed',
  'logout',
  'playback',
  'download',
  'like',
  'unlike',
  'delete',
  'audio_replaced',
  'device_paired',
  'device_unpaired',
  'user_created',
  'user_updated',
  'user_deleted',
  'password_changed',
  'settings_changed',
]

const ICONS = {
  login: 'log-in',
  login_failed: 'alert',
  logout: 'log-out',
  playback: 'play',
  download: 'download',
  like: 'heart',
  unlike: 'heart-outline',
  delete: 'trash',
  audio_replaced: 'retry',
  device_paired: 'monitor',
  device_unpaired: 'monitor',
  user_created: 'users',
  user_updated: 'users',
  user_deleted: 'users',
  password_changed: 'key',
  settings_changed: 'settings',
}

/** The icon for an entry of `kind`. */
export function activityIcon(kind) {
  return ICONS[kind] || 'activity'
}
