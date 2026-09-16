import { computed } from 'vue'
import { useProgressTracker } from '/src/model/download'

/** Downloads still waiting or running — the Queue badge. */
export function usePendingCount() {
  const { downloadQueue, queueVersion } = useProgressTracker()
  return computed(() => {
    queueVersion.value
    return downloadQueue.value.filter(
      (item) => item.isQueued() || item.isDownloading()
    ).length
  })
}
