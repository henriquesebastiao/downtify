/**
 * Pure visibility rules for the mini player bar and its "restore"
 * button — deliberately zero-import so it's unit-testable without
 * pulling in the browser-dependent player/settings/router modules that
 * the reactive composable (`useMiniPlayer` in `miniPlayer.js`) wraps
 * this in.
 *
 * The bar never shows on the Player page itself (it already has full
 * controls), with nothing loaded, or with the feature turned off in
 * Settings; otherwise it's either the bar or the restore button,
 * never both, based on whether the user collapsed it.
 */
export function miniPlayerVisibility({
  enabled,
  hasCurrentTrack,
  isPlayerRoute,
  collapsed,
}) {
  const shouldShow = enabled && hasCurrentTrack && !isPlayerRoute
  return {
    showBar: shouldShow && !collapsed,
    showRestoreButton: shouldShow && collapsed,
  }
}
