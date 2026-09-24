<template>
  <header
    class="relative isolate flex flex-col justify-end overflow-hidden"
    :class="banner ? 'min-h-[300px] sm:min-h-[380px] lg:min-h-[440px]' : ''"
  >
    <img
      v-if="banner"
      :src="banner"
      alt=""
      class="absolute inset-0 -z-20 size-full object-cover object-[center_20%]"
    />
    <div
      class="absolute inset-0 -z-10"
      :class="banner ? '' : 'opacity-70'"
      :style="{
        background: banner
          ? 'linear-gradient(180deg, rgba(11,12,14,0.05) 0%, rgba(11,12,14,0.55) 65%, rgba(11,12,14,0.92) 100%)'
          : `linear-gradient(180deg, ${tint} 0%, transparent 100%)`,
      }"
      aria-hidden="true"
    />
    <button
      v-if="bannerEditable"
      type="button"
      :title="t('artistArt.editArtist')"
      :aria-label="t('artistArt.editArtist')"
      class="absolute top-4 right-4 z-10 flex size-10 items-center justify-center rounded-full border border-line-2 bg-black/55 text-white backdrop-blur transition-colors hover:bg-black/70"
      @click="$emit('edit-banner')"
    >
      <AppIcon name="pencil" :size="16" />
    </button>
    <div
      v-if="banner && (socialLinks.length || platformLinks.length)"
      class="absolute right-4 bottom-4 z-10 flex flex-col items-end gap-2"
    >
      <div v-if="socialLinks.length" class="flex items-center gap-2">
        <a
          v-for="link in socialLinks"
          :key="link.key"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          :title="link.label"
          :aria-label="link.label"
          class="flex size-9 items-center justify-center rounded-full border border-line-2 bg-black/55 text-white backdrop-blur transition-colors hover:bg-black/70"
        >
          <AppIcon :name="link.icon" :size="16" />
        </a>
      </div>
      <div v-if="platformLinks.length" class="flex items-center gap-2">
        <a
          v-for="link in platformLinks"
          :key="link.key"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          :title="link.label"
          :aria-label="link.label"
          class="flex size-9 items-center justify-center rounded-full border border-line-2 bg-black/55 text-white backdrop-blur transition-colors hover:bg-black/70"
        >
          <AppIcon :name="link.icon" :size="16" />
        </a>
      </div>
    </div>
    <div
      class="mr-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 pb-6 sm:px-6 md:flex-row md:items-end md:gap-8 md:pt-10 lg:px-10"
    >
      <div
        v-if="!banner"
        class="group/cover relative size-48 shrink-0 self-center sm:size-56 md:self-auto lg:size-[232px]"
      >
        <CoverArt
          :src="cover"
          :fallback="coverFallback"
          :covers="covers"
          :name="name || title"
          :round="round"
          :icon="icon"
          :symbol="symbol"
          shadow
          :letter-size="96"
          :icon-size="64"
          rounded="rounded-[16px]"
          class="size-full shadow-[0_24px_60px_rgba(0,0,0,0.45)]"
        />
        <button
          v-if="photoEditable"
          type="button"
          class="absolute inset-0 flex items-center justify-center rounded-[16px] bg-black/0 text-white opacity-0 transition-all group-hover/cover:bg-black/45 group-hover/cover:opacity-100"
          :class="round ? 'rounded-full' : ''"
          @click="$emit('edit-photo')"
        >
          <span class="flex items-center gap-2 text-base font-semibold">
            <AppIcon name="pencil" :size="17" />{{ t('artistArt.editPhoto') }}
          </span>
        </button>
      </div>
      <div
        class="flex min-w-0 flex-col gap-3 max-md:items-center max-md:text-center"
      >
        <span
          class="eyebrow"
          :class="banner ? '!text-white/70' : '!text-fg-3'"
          >{{ kicker }}</span
        >
        <h1
          class="text-display line-clamp-2 text-4xl leading-[1.05] font-bold text-balance break-words sm:text-5xl xl:text-[64px]"
          :class="banner ? 'text-white' : 'text-fg'"
        >
          {{ title }}
        </h1>
        <p class="text-[15px]" :class="banner ? 'text-white/75' : 'text-fg-3'">
          <slot name="subtitle" />
        </p>
        <div
          class="mt-3 flex flex-wrap items-center gap-2.5 max-md:justify-center"
        >
          <slot name="actions" />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import { hueFor } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const props = defineProps({
  title: { type: String, required: true },
  kicker: { type: String, default: '' },
  name: { type: String, default: '' },
  cover: { type: String, default: '' },
  // Shown when `cover` fails to load (see CoverArt) - for a `cover` that
  // may not exist, like an artist photo from the proxy.
  coverFallback: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  icon: { type: String, default: 'disc' },
  symbol: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  // Optional background photo (artist page only - see ArtistView) and
  // whether each hover "edit photo/banner" affordance is shown at all -
  // each mirrors its own settings toggle independently. When a banner
  // is set, the round photo (and its own edit affordance) is hidden
  // entirely to de-clutter the header - ArtistArtModal's "Profile" tab
  // is still reachable from the banner's edit button.
  banner: { type: String, default: '' },
  photoEditable: { type: Boolean, default: false },
  bannerEditable: { type: Boolean, default: false },
  // Artist profile links (see downtify/artist_profile.py) - only rendered
  // over the banner, bottom-right, as two rows of icon links: social
  // first, then streaming platforms. Each object's empty/unknown keys are
  // silently skipped, so an artist with nothing saved yet shows neither.
  social: { type: Object, default: () => ({}) },
  platformsId: { type: Object, default: () => ({}) },
})
defineEmits(['edit-photo', 'edit-banner'])

const { t } = useI18n()

const tint = computed(
  () => `oklch(0.45 0.08 ${hueFor(props.name || props.title)} / 0.55)`
)

const SOCIAL_LINKS = {
  twitter: { icon: 'twitter', label: 'Twitter/X' },
  instagram: { icon: 'instagram', label: 'Instagram' },
  facebook: { icon: 'facebook', label: 'Facebook' },
  youtube: { icon: 'youtube', label: 'YouTube' },
  website: { icon: 'globe', label: 'Website' },
}
const socialLinks = computed(() =>
  Object.keys(SOCIAL_LINKS)
    .filter((key) => String(props.social?.[key] || '').trim())
    .map((key) => ({
      key,
      url: String(props.social[key]).trim(),
      ...SOCIAL_LINKS[key],
    }))
)

// Base URL each platform's saved id is appended to. The backend resolves
// all four automatically (see downtify/artist_profile.py) and a hand-edit
// of the profile JSON can set any of them. Unrecognized keys are skipped
// rather than erroring, so this grows without a frontend change needed
// elsewhere.
const PLATFORM_LINKS = {
  spotify: {
    icon: 'spotify',
    label: 'Spotify',
    prefix: 'https://open.spotify.com/artist/',
  },
  youtubemusic: {
    icon: 'youtube-music',
    label: 'YouTube Music',
    prefix: 'https://music.youtube.com/channel/',
  },
  deezer: {
    icon: 'deezer',
    label: 'Deezer',
    prefix: 'https://www.deezer.com/artist/',
  },
  // Stored as 'slug/numeric-id' (e.g. 'evanescence/42102393', straight
  // from Apple's own `url` field) - the 'us' storefront in this prefix
  // is just a stable link target, not tied to the artist's real catalog
  // availability elsewhere.
  applemusic: {
    icon: 'apple-music',
    label: 'Apple Music',
    prefix: 'https://music.apple.com/us/artist/',
  },
}
const platformLinks = computed(() =>
  Object.keys(PLATFORM_LINKS)
    .filter((key) => String(props.platformsId?.[key] || '').trim())
    .map((key) => ({
      key,
      url: `${PLATFORM_LINKS[key].prefix}${String(props.platformsId[key]).trim()}`,
      icon: PLATFORM_LINKS[key].icon,
      label: PLATFORM_LINKS[key].label,
    }))
)
</script>
