<template>
  <UiModal
    :open="Boolean(target)"
    :title="t('buy.title')"
    :description="t('buy.body')"
    width="sm:max-w-lg"
    @close="close"
  >
    <div v-if="target" class="flex flex-col gap-4">
      <p class="truncate text-sm font-semibold">{{ heading }}</p>

      <ul v-if="loading" class="flex flex-col gap-2" aria-busy="true">
        <li
          v-for="n in 3"
          :key="n"
          class="h-[66px] animate-pulse rounded-[12px] bg-surface-2"
        />
      </ul>
      <div
        v-else-if="error"
        class="flex items-center justify-between gap-3"
        role="alert"
      >
        <p class="text-[13px] text-danger">{{ t('buy.failed') }}</p>
        <UiButton variant="ghost" size="sm" icon="refresh" @click="fetchLinks">
          {{ t('common.retry') }}
        </UiButton>
      </div>
      <ul v-else class="flex flex-col gap-2">
        <li v-for="link in links" :key="link.store">
          <a
            :href="link.href"
            target="_blank"
            rel="noopener noreferrer"
            class="group flex items-center gap-3 rounded-[12px] border border-line-2 bg-surface px-4 py-3 transition-colors hover:bg-surface-2"
          >
            <span
              class="grid size-10 shrink-0 place-items-center rounded-full bg-surface-2 text-fg"
            >
              <AppIcon :name="link.icon" :size="18" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold">{{
                link.label
              }}</span>
              <span class="block truncate text-[12px] text-muted">{{
                link.detail
              }}</span>
            </span>
            <UiBadge v-if="link.price" tone="accent">{{ link.price }}</UiBadge>
            <AppIcon
              name="arrow-up-right"
              :size="16"
              class="shrink-0 text-faint transition-colors group-hover:text-fg"
            />
          </a>
        </li>
      </ul>

      <p class="text-[12px] text-faint">{{ t('buy.note') }}</p>
    </div>
  </UiModal>
</template>

<script setup>
// "Support the artist": where to buy the song, album or artist on screen
// (the iTunes Store item when the store has it, Bandcamp and Qobuz
// searches, the artist's own website) - see downtify/buy_links.py.
import { computed, ref, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiModal from '../ui/UiModal.vue'
import { useBuyLinks } from '/src/model/buyLinks'
import { formatPrice, storeIcon } from '/src/lib/buyLinks'
import { linkHost, safeLinkUrl } from '/src/lib/artistLinks'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const { target, close, load } = useBuyLinks()

const answer = ref(null)
const loading = ref(false)
const error = ref(false)

const heading = computed(() => {
  const item = target.value
  if (!item) return ''
  const name = item.title || item.album
  return name ? `${name} · ${item.artist}` : item.artist
})

function detailFor(link, query) {
  if (link.store === 'website') return linkHost(link.url)
  if (link.match) return t('buy.inStore')
  return t('buy.search', { query })
}

const links = computed(() =>
  (answer.value?.links || [])
    .map((link) => ({
      store: link.store,
      href: safeLinkUrl(link.url),
      icon: storeIcon(link.store),
      label: link.store === 'website' ? t('buy.website') : link.label,
      detail: detailFor(link, answer.value.query),
      price: formatPrice(link.price, link.currency, locale.value),
    }))
    .filter((link) => link.href)
)

async function fetchLinks() {
  const item = target.value
  if (!item) return
  loading.value = true
  error.value = false
  try {
    const data = await load(item)
    // Another song may have been opened meanwhile.
    if (target.value === item) answer.value = data
  } catch {
    if (target.value === item) error.value = true
  } finally {
    if (target.value === item) loading.value = false
  }
}

watch(target, (item) => {
  answer.value = null
  if (item) fetchLinks()
})
</script>
