// Wording for Settings > Server > Backups (BackupSettings.vue).

/** Query flags for a restore: `{settings, watches, songs}` -> `'1'|'0'`. */
export function restoreParams(parts) {
  const params = {}
  for (const part of ['settings', 'watches', 'songs']) {
    params[part] = parts?.[part] ? '1' : '0'
  }
  return params
}

/** One line on what a restore did (the restore response). */
export function restoreSummary(result, t) {
  if (!result) return ''
  const lines = []
  if (result.settings?.length) lines.push(t('backup.resultSettings'))
  if (result.watches_added || result.watches_present) {
    lines.push(
      t('backup.resultWatches', {
        added: result.watches_added || 0,
        present: result.watches_present || 0,
      })
    )
  }
  if (result.songs_missing) {
    lines.push(
      t('backup.resultSongs', {
        missing: result.songs_missing,
        queued: result.songs_queued || 0,
      })
    )
  } else if (result.songs_checked) {
    lines.push(t('backup.resultNoSongs'))
  }
  return lines.join(' · ')
}
