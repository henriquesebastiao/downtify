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
          <h3 class="text-lg font-bold tracking-tight">Settings</h3>
          <p class="text-xs text-base-content/50 mt-0.5">
            Tweak how Downtify fetches and tags your music.
          </p>
        </div>
        <label
          for="settings-modal"
          class="icon-btn cursor-pointer"
          title="Close"
        >
          <Icon icon="clarity:close-line" class="h-5 w-5" />
        </label>
      </div>

      <!-- Body -->
      <div class="px-6 py-5 space-y-6">
        <!-- Audio source -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            Audio source
          </label>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="provider in sm.settingsOptions.audio_providers"
              :key="provider"
              type="button"
              class="rounded-xl border px-3 py-2 text-sm transition-colors text-left"
              :class="[
                sm.settings.value.audio_providers[0] === provider
                  ? 'border-primary/50 bg-primary/10 text-primary'
                  : 'border-white/10 hover:border-white/20 hover:bg-white/5',
              ]"
              @click="sm.settings.value.audio_providers = [provider]"
            >
              {{ providerLabel(provider) }}
            </button>
          </div>
        </div>

        <!-- Lyrics source -->
        <div>
          <div class="flex items-baseline justify-between mb-2">
            <label
              class="block text-xs font-semibold uppercase tracking-wider text-base-content/50"
            >
              Lyrics source
            </label>
            <span class="text-[10px] text-base-content/40">
              only lrclib is active
            </span>
          </div>
          <select
            class="select w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
            v-model="sm.settings.value.lyrics_providers[0]"
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
              Format
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
                Quality
              </label>
              <span
                v-if="sm.settings.value.format === 'flac'"
                class="text-[10px] text-base-content/40"
              >
                ignored (lossless)
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
            Playlists
          </label>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.generate_m3u"
            />
            <span class="flex-1 text-sm">
              <span class="block">Generate M3U file for playlists</span>
              <span class="block text-[11px] text-base-content/50">
                Writes <code>Playlists/&lt;name&gt;.m3u</code> alongside the
                tracks for both manual playlist downloads and Playlist Monitor
                sweeps.
              </span>
            </span>
          </label>
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
            Changes saved
          </div>
          <div
            v-else-if="sm.isSaved.value === false"
            class="surface rounded-xl p-3 flex items-center gap-2 text-sm text-error"
          >
            <Icon
              icon="clarity:exclamation-circle-line"
              class="h-4 w-4 shrink-0"
            />
            Couldn't save settings.
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
          Cancel
        </label>
        <button
          class="btn btn-primary btn-sm h-10 px-6 rounded-full"
          @click="sm.saveSettings()"
        >
          Save
        </button>
      </div>
    </div>
    <label class="modal-backdrop" for="settings-modal">Close</label>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import { useSettingsManager } from '../model/settings'

const sm = useSettingsManager()

function providerLabel(provider) {
  if (provider === 'youtube-music') return 'YouTube Music'
  if (provider === 'youtube') return 'YouTube'
  return provider
}
</script>
