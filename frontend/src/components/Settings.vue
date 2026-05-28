<template>
  <input type="checkbox" id="settings-modal" class="modal-toggle" />
  <div class="modal modal-bottom sm:modal-middle">
    <div
      class="modal-box surface-strong rounded-t-3xl sm:rounded-3xl p-0 max-w-lg"
    >
      <!-- Header -->
      <div
        class="flex items-center justify-between px-6 py-4 border-b border-white/5"
      >
        <div>
          <h3 class="text-lg font-bold tracking-tight">
            {{ t('settings.title') }}
          </h3>
          <p class="text-xs text-base-content/50 mt-0.5">
            {{ t('settings.subtitle') }}
          </p>
        </div>
        <label
          for="settings-modal"
          class="icon-btn cursor-pointer"
          :title="t('common.close')"
        >
          <Icon icon="clarity:close-line" class="h-5 w-5" />
        </label>
      </div>

      <!-- Body -->
      <div class="px-6 py-5 space-y-6">
        <!-- Language -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.language') }}
          </label>
          <select
            class="select w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
            :value="locale"
            @change="setLocale($event.target.value)"
          >
            <option v-for="l in locales" :key="l.code" :value="l.code">
              {{ l.name }}
            </option>
          </select>
          <p class="text-[11px] text-base-content/40 mt-1.5">
            {{ t('settings.languageHint') }}
          </p>
        </div>

        <!-- Audio source -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.audioSource') }}
          </label>
          <p class="text-[11px] text-base-content/40 mb-2">
            {{ t('settings.audioSourceHint') }}
          </p>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="provider in sm.settingsOptions.audio_providers"
              :key="provider"
              type="button"
              class="rounded-xl border px-3 py-2 text-sm transition-colors text-left relative"
              :class="[
                audioProviderIndex(provider) >= 0
                  ? 'border-primary/50 bg-primary/10 text-primary'
                  : 'border-white/10 hover:border-white/20 hover:bg-white/5',
              ]"
              @click="toggleAudioProvider(provider)"
            >
              <span
                v-if="audioProviderIndex(provider) >= 0"
                class="absolute top-1 right-1 text-[10px] font-bold opacity-80"
              >
                {{ audioProviderIndex(provider) + 1 }}
              </span>
              {{ providerLabel(provider) }}
            </button>
          </div>
          <ul
            v-if="sm.settings.value.audio_providers.length"
            class="mt-2 space-y-1 text-sm"
          >
            <li
              v-for="(provider, index) in sm.settings.value.audio_providers"
              :key="provider"
              class="flex items-center gap-2 rounded-lg border border-white/10 px-2 py-1"
            >
              <span class="text-xs opacity-50 w-4">{{ index + 1 }}</span>
              <span class="flex-1">{{ providerLabel(provider) }}</span>
              <button
                type="button"
                class="btn btn-xs btn-ghost px-1 min-h-0 h-7"
                :disabled="index === 0"
                @click="moveProviderAt(index, -1)"
              >
                ↑
              </button>
              <button
                type="button"
                class="btn btn-xs btn-ghost px-1 min-h-0 h-7"
                :disabled="index === sm.settings.value.audio_providers.length - 1"
                @click="moveProviderAt(index, 1)"
              >
                ↓
              </button>
            </li>
          </ul>
          <button
            type="button"
            class="btn btn-xs btn-ghost rounded-lg mt-2"
            @click="resetAudioProvidersRecommended"
          >
            {{ t('settings.audioSourceReset') }}
          </button>
        </div>

        <!-- slskd -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.slskdSection') }}
          </label>
          <p class="text-[11px] text-base-content/40 mb-2">
            {{ t('settings.slskdHint') }}
          </p>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20 mb-2"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.slskd.enabled"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.slskdEnabled') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.slskdEnabledHint') }}
              </span>
            </span>
          </label>
          <div
            v-if="sm.settings.value.slskd.enabled"
            class="grid grid-cols-1 gap-2"
          >
            <input
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              type="text"
              :placeholder="t('settings.slskdBaseUrl')"
              v-model="sm.settings.value.slskd.base_url"
            />
            <input
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              type="password"
              :placeholder="t('settings.slskdApiKey')"
              v-model="sm.settings.value.slskd.api_key"
            />
            <div class="rounded-xl border border-white/10 bg-base-100/50 px-3 py-2.5 space-y-2">
              <p class="text-[11px] font-semibold text-base-content/70">
                {{ t('settings.slskdSourceDirTitle') }}
              </p>
              <ul class="text-[11px] text-base-content/50 space-y-1 list-disc pl-4">
                <li>{{ t('settings.slskdSourceDirBullet1') }}</li>
                <li>{{ t('settings.slskdSourceDirBullet2') }}</li>
                <li>{{ t('settings.slskdSourceDirBullet3') }}</li>
              </ul>
              <pre
                class="text-[10px] leading-relaxed text-base-content/60 whitespace-pre-wrap font-mono bg-base-300/30 rounded-lg px-2 py-1.5"
              >{{ t('settings.slskdSourceDirExample') }}</pre>
            </div>
            <label class="text-[11px] text-base-content/50">
              {{ t('settings.slskdSourceDirLabel') }}
            </label>
            <input
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60 font-mono text-sm"
              type="text"
              :placeholder="t('settings.slskdSourceDirPlaceholder')"
              v-model="sm.settings.value.slskd.source_dir"
            />
            <p class="text-[11px] text-base-content/40">
              {{ t('settings.slskdSourceDirHint') }}
            </p>
            <label
              class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20 mt-2"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-sm checkbox-primary mt-0.5"
                v-model="sm.settings.value.slskd.leave_in_place"
              />
              <span>
                <span class="block text-sm font-medium">{{
                  t('settings.slskdLeaveInPlace')
                }}</span>
                <span class="block text-[11px] text-base-content/50 mt-0.5">{{
                  t('settings.slskdLeaveInPlaceHint')
                }}</span>
              </span>
            </label>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
              <label class="text-[11px] text-base-content/50">
                {{ t('settings.slskdDownloadTimeout') }}
                <input
                  class="input input-sm w-full mt-1 rounded-xl bg-base-100/85 border border-white/10"
                  type="number"
                  min="30"
                  max="3600"
                  v-model.number="sm.settings.value.slskd.download_timeout_seconds"
                />
              </label>
              <label class="text-[11px] text-base-content/50">
                {{ t('settings.slskdQueuedTimeout') }}
                <input
                  class="input input-sm w-full mt-1 rounded-xl bg-base-100/85 border border-white/10"
                  type="number"
                  min="15"
                  max="3600"
                  v-model.number="sm.settings.value.slskd.queued_timeout_seconds"
                />
              </label>
            </div>
            <p class="text-[11px] text-base-content/40">
              {{ t('settings.slskdTimeoutHint') }}
            </p>
          </div>
        </div>

        <!-- Lyrics source -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.lyricsSource') }}
          </label>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20 mb-2"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.download_lyrics"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.downloadLyrics') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.downloadLyricsHint') }}
              </span>
            </span>
          </label>
          <div class="flex items-baseline justify-between mb-1.5">
            <span class="text-xs text-base-content/50">
              {{ t('settings.lyricsProvider') }}
            </span>
            <span class="text-[10px] text-base-content/40">
              {{ t('settings.lyricsHint') }}
            </span>
          </div>
          <select
            class="select w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60 disabled:opacity-40"
            v-model="sm.settings.value.lyrics_providers[0]"
            :disabled="!sm.settings.value.download_lyrics"
          >
            <option
              v-for="provider in sm.settingsOptions.lyrics_providers"
              :key="provider"
              :value="provider"
            >
              {{ provider }}
            </option>
          </select>
        </div>

        <!-- Format & bitrate -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label
              class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
            >
              {{ t('settings.format') }}
            </label>
            <select
              class="select w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              v-model="sm.settings.value.format"
            >
              <option
                v-for="fmt in sm.settingsOptions.format"
                :key="fmt"
                :value="fmt"
              >
                {{ fmt.toUpperCase() }}
              </option>
            </select>
          </div>
          <div>
            <div class="flex items-baseline justify-between mb-2">
              <label
                class="block text-xs font-semibold uppercase tracking-wider text-base-content/50"
              >
                {{ t('settings.quality') }}
              </label>
              <span
                v-if="sm.settings.value.format === 'flac'"
                class="text-[10px] text-base-content/40"
              >
                {{ t('settings.qualityIgnored') }}
              </span>
            </div>
            <select
              class="select w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              v-model="sm.settings.value.bitrate"
              :disabled="sm.settings.value.format === 'flac'"
            >
              <option
                v-for="bitrate in sm.settingsOptions.bitrate"
                :key="bitrate"
                :value="bitrate"
              >
                {{ bitrate }} kbps
              </option>
            </select>
          </div>
        </div>

        <!-- Playlists -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.playlistsSection') }}
          </label>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20 mb-2"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.generate_m3u"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.generateM3u') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.generateM3uHint') }}
              </span>
            </span>
          </label>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.sync_navidrome"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.syncNavidrome') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.syncNavidromeHint') }}
              </span>
            </span>
          </label>
        </div>

        <!-- Navidrome -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.navidromeSection') }}
          </label>
          <p class="text-[11px] text-base-content/40 mb-2">
            {{ t('settings.navidromeHint') }}
          </p>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20 mb-2"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.navidrome.enabled"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.navidromeEnabled') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.navidromeEnabledHint') }}
              </span>
            </span>
          </label>
          <div
            v-if="sm.settings.value.navidrome.enabled"
            class="grid grid-cols-1 gap-2"
          >
            <input
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              type="text"
              :placeholder="t('settings.navidromeUrl')"
              v-model="sm.settings.value.navidrome.url"
            />
            <input
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              type="text"
              :placeholder="t('settings.navidromeUsername')"
              v-model="sm.settings.value.navidrome.username"
            />
            <input
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              type="password"
              :placeholder="t('settings.navidromePassword')"
              v-model="sm.settings.value.navidrome.password"
            />
            <input
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              type="text"
              :placeholder="t('settings.navidromeAdminUser')"
              v-model="sm.settings.value.navidrome.admin_username"
            />
            <input
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              type="password"
              :placeholder="t('settings.navidromeAdminPassword')"
              v-model="sm.settings.value.navidrome.admin_password"
            />
            <label
              class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-sm checkbox-primary mt-0.5"
                v-model="sm.settings.value.navidrome.public_playlist"
              />
              <span class="flex-1 text-sm">
                <span class="block">{{ t('settings.navidromePublic') }}</span>
              </span>
            </label>
          </div>
        </div>

        <!-- File organization -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.organizationSection') }}
          </label>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.organize_by_artist"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.organizeByArtist') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.organizeByArtistHint') }}
              </span>
            </span>
          </label>
        </div>

        <!-- Parallel downloads -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.parallelDownloads') }}
          </label>
          <div class="grid grid-cols-5 gap-1.5">
            <button
              v-for="n in sm.settingsOptions.max_parallel_downloads"
              :key="n"
              type="button"
              class="rounded-xl border px-2 py-2 text-sm font-medium transition-colors text-center"
              :class="[
                sm.settings.value.max_parallel_downloads === n
                  ? 'border-primary/50 bg-primary/10 text-primary'
                  : 'border-white/10 hover:border-white/20 hover:bg-white/5',
              ]"
              @click="sm.settings.value.max_parallel_downloads = n"
            >
              {{ n }}
            </button>
          </div>
          <p class="text-[11px] text-base-content/40 mt-1.5">
            {{ t('settings.parallelDownloadsHint') }}
          </p>
        </div>

        <!-- Save status -->
        <transition
          enter-active-class="transition duration-200"
          enter-from-class="opacity-0 -translate-y-1"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-200"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <div
            v-if="sm.isSaved.value === true"
            class="surface rounded-xl p-3 flex items-center gap-2 text-sm text-primary"
          >
            <Icon icon="clarity:check-line" class="h-4 w-4 shrink-0" />
            {{ t('settings.saved') }}
          </div>
          <div
            v-else-if="sm.isSaved.value === false"
            class="surface rounded-xl p-3 flex items-center gap-2 text-sm text-error"
          >
            <Icon
              icon="clarity:exclamation-circle-line"
              class="h-4 w-4 shrink-0"
            />
            {{ sm.saveErrorText.value || t('settings.saveError') }}
          </div>
        </transition>
      </div>

      <!-- Footer -->
      <div
        class="flex items-center justify-end gap-2 px-6 py-4 border-t border-white/5"
      >
        <label
          for="settings-modal"
          class="btn btn-sm h-10 px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100 cursor-pointer"
        >
          {{ t('common.cancel') }}
        </label>
        <button
          class="btn btn-primary btn-sm h-10 px-6 rounded-full"
          @click="sm.saveSettings()"
        >
          {{ t('common.save') }}
        </button>
      </div>
    </div>
    <label class="modal-backdrop" for="settings-modal">{{
      t('common.close')
    }}</label>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import { watchEffect } from 'vue'
import { useSettingsManager } from '../model/settings'
import { useI18n } from '../i18n'

const sm = useSettingsManager()
const { t, locale, setLocale, locales } = useI18n()

const NAVIDROME_DEFAULTS = {
  enabled: false,
  url: '',
  username: '',
  password: '',
  admin_username: '',
  admin_password: '',
  public_playlist: false,
  scan_after_download: true,
  scan_wait_seconds: 120,
  scan_poll_seconds: 30,
  client_name: 'Downtify',
  api_version: '1.16.1',
}

const SLSKD_DEFAULTS = {
  enabled: false,
  base_url: '',
  api_key: '',
  source_dir: '/slskd',
  leave_in_place: true,
  timeout_seconds: 20,
  search_retries: 5,
  search_poll_seconds: 15,
  download_attempts: 3,
  poll_interval_seconds: 5,
  poll_max_attempts: 60,
  download_timeout_seconds: 600,
  queued_timeout_seconds: 180,
  extensions: ['mp3', 'flac'],
  min_bitrate: 256,
}

watchEffect(() => {
  const curr = sm.settings.value?.slskd
  if (!curr || typeof curr !== 'object') {
    sm.settings.value.slskd = { ...SLSKD_DEFAULTS }
    return
  }
  for (const [k, v] of Object.entries(SLSKD_DEFAULTS)) {
    if (curr[k] === undefined || curr[k] === null) {
      curr[k] = v
    }
  }
})

watchEffect(() => {
  const curr = sm.settings.value?.navidrome
  if (!curr || typeof curr !== 'object') {
    sm.settings.value.navidrome = { ...NAVIDROME_DEFAULTS }
    return
  }
  for (const [k, v] of Object.entries(NAVIDROME_DEFAULTS)) {
    if (curr[k] === undefined || curr[k] === null) {
      curr[k] = v
    }
  }
})

watchEffect(() => {
  if (sm.settings.value?.sync_navidrome === undefined) {
    sm.settings.value.sync_navidrome = true
  }
})

watchEffect(() => {
  const providers = sm.settings.value?.audio_providers
  if (!Array.isArray(providers) || providers.length === 0) {
    sm.settings.value.audio_providers = ['youtube-music']
  }
})

function providerLabel(provider) {
  if (provider === 'youtube-music') return 'YouTube Music'
  if (provider === 'youtube') return 'YouTube'
  if (provider === 'slskd') return 'slskd'
  return provider
}

const AUDIO_PROVIDER_ORDER = ['slskd', 'youtube-music', 'youtube']

function audioProviderIndex(provider) {
  const list = sm.settings.value?.audio_providers || []
  return list.indexOf(provider)
}

function toggleAudioProvider(provider) {
  const list = [...(sm.settings.value.audio_providers || [])]
  const idx = list.indexOf(provider)
  if (idx >= 0) {
    list.splice(idx, 1)
  } else {
    list.push(provider)
  }
  sm.settings.value.audio_providers =
    list.length > 0 ? list : ['youtube-music']
}

function moveProviderAt(index, delta) {
  const list = [...(sm.settings.value.audio_providers || [])]
  const target = index + delta
  if (target < 0 || target >= list.length) return
  ;[list[index], list[target]] = [list[target], list[index]]
  sm.settings.value.audio_providers = list
}

function resetAudioProvidersRecommended() {
  const slskdOn = Boolean(sm.settings.value?.slskd?.enabled)
  sm.settings.value.audio_providers = slskdOn
    ? [...AUDIO_PROVIDER_ORDER]
    : ['youtube-music', 'youtube']
}
</script>
