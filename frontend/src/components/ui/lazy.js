// Parts of a page that only some visits need (one settings section, a
// Now playing panel) are loaded when first shown, with a skeleton in their
// place meanwhile - no delay here, the skeleton holds itself back so a
// quick load never flashes it (styles/motion.css → .skeleton).
import { defineAsyncComponent } from 'vue'
import UiPanelSkeleton from './UiPanelSkeleton.vue'

export function lazyComponent(loader, loadingComponent = UiPanelSkeleton) {
  return defineAsyncComponent({ loader, loadingComponent, delay: 0 })
}
