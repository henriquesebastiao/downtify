<template>
  <div ref="root" class="relative" :style="{ height: `${totalSize}px` }">
    <div
      v-for="row in rows"
      :key="row.index"
      :ref="measure"
      :data-index="row.index"
      class="absolute inset-x-0 top-0"
      :class="layout === 'grid' ? 'pb-7' : ''"
      :style="{ transform: `translateY(${row.start}px)` }"
    >
      <div v-if="layout === 'grid'" :class="GRID_CLASS">
        <template v-for="item in row.items" :key="itemKey(item)">
          <slot :item="item" />
        </template>
      </div>
      <template v-else>
        <template v-for="item in row.items" :key="itemKey(item)">
          <slot :item="item" />
        </template>
      </template>
    </div>
  </div>
</template>

<script setup>
// Renders only the rows of a big tile grid (or list) that are on screen,
// like TrackList does for tracks: a Library with ~3,700 albums used to
// mount every tile at once (~60,000 DOM nodes) and keep every cover the
// user scrolled past decoded in memory.
import { computed, onMounted, ref, watch } from 'vue'
import { useElementSize, useWindowSize } from '@vueuse/core'
import { useWindowVirtualizer } from '@tanstack/vue-virtual'
import { columnsFor, estimateRowHeight, rowItems } from '/src/lib/virtualGrid'

const props = defineProps({
  items: { type: Array, default: () => [] },
  itemKey: { type: Function, default: (item) => item.key },
  // 'grid': tiles in responsive columns; 'list': one item per row.
  layout: { type: String, default: 'grid' },
  // Row height of the list layout, px.
  rowHeight: { type: Number, default: 72 },
})

// Must match columnsFor() in lib/virtualGrid.js.
const GRID_CLASS =
  'grid grid-cols-2 gap-x-4 xs:gap-x-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6 min-[1900px]:grid-cols-7'

const root = ref(null)
const scrollMargin = ref(0)
const { width: windowWidth } = useWindowSize()
const { width: rootWidth } = useElementSize(root)

const columns = computed(() =>
  props.layout === 'grid' ? columnsFor(windowWidth.value) : 1
)
const rowCount = computed(() => Math.ceil(props.items.length / columns.value))

const virtualizer = useWindowVirtualizer(
  computed(() => ({
    count: rowCount.value,
    estimateSize: () =>
      props.layout === 'grid'
        ? estimateRowHeight(rootWidth.value, columns.value, windowWidth.value)
        : props.rowHeight,
    overscan: 3,
    scrollMargin: scrollMargin.value,
  }))
)

function measure(el) {
  if (el) virtualizer.value.measureElement(el)
}

function measureOffset() {
  if (!root.value) return
  scrollMargin.value = root.value.getBoundingClientRect().top + window.scrollY
}
onMounted(measureOffset)
watch(
  () => [props.items.length, windowWidth.value],
  () => requestAnimationFrame(measureOffset)
)
// Rows hold a different number of tiles (and are a different height)
// once the column count or width changes: measure them again.
watch([columns, rootWidth], () => virtualizer.value.measure())

const totalSize = computed(() => virtualizer.value.getTotalSize())

const rows = computed(() =>
  virtualizer.value.getVirtualItems().map((row) => ({
    index: row.index,
    start: row.start - scrollMargin.value,
    items: rowItems(props.items, row.index, columns.value),
  }))
)
</script>
