<template>
  <input type="checkbox" id="settings-modal" class="modal-toggle" />
  <div class="modal modal-bottom sm:modal-middle">
    <div
      class="modal-box surface-strong rounded-t-3xl sm:rounded-3xl p-0 max-w-lg overflow-hidden flex flex-col"
    >
      <!-- Header -->
      <!-- overflow-hidden + flex-col on modal-box (above) clips the body's
           scrollbar to the rounded corners instead of it poking past them
           (daisyUI's .modal-box ships overflow-y:auto directly on the
           rounded element, which native scrollbars don't respect). -->
      <div
        class="shrink-0 flex items-center justify-between px-6 py-4 border-b border-white/5"
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
          <Icon icon="fa6-solid:xmark" class="h-5 w-5" />
        </label>
      </div>

      <!-- Body -->
      <div class="px-6 py-5 space-y-6 overflow-y-auto min-h-0">
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
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="provider in sm.settingsOptions.audio_providers"
              :key="provider"
              type="button"
              class="relative rounded-xl border px-3 py-2 text-sm transition-colors text-left"
              :class="[
                providerIndex(provider) >= 0
                  ? 'border-primary/50 bg-primary/10 text-primary'
                  : 'border-white/10 hover:border-white/20 hover:bg-white/5',
              ]"
              @click="toggleProvider(provider)"
            >
              <span
                v-if="providerIndex(provider) >= 0"
                class="absolute top-1 right-1.5 text-[10px] font-bold opacity-80"
              >
                {{ providerIndex(provider) + 1 }}
              </span>
              {{ providerLabel(provider) }}
            </button>
          </div>
          <ul
            v-if="sm.settings.value.audio_providers.length > 1"
            class="mt-2 space-y-1"
          >
            <li
              v-for="(provider, index) in sm.settings.value.audio_providers"
              :key="provider"
              class="flex items-center gap-2 rounded-xl border border-white/10 px-3 py-1 text-sm"
            >
              <span class="w-4 text-xs text-base-content/50">{{
                index + 1
              }}</span>
              <span class="flex-1">{{ providerLabel(provider) }}</span>
              <button
                type="button"
                class="icon-btn h-8 w-8"
                :disabled="index === 0"
                :title="t('settings.audioSourceMoveUp')"
                @click="moveProvider(index, -1)"
              >
                <Icon icon="fa6-solid:chevron-up" class="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                class="icon-btn h-8 w-8"
                :disabled="
                  index === sm.settings.value.audio_providers.length - 1
                "
                :title="t('settings.audioSourceMoveDown')"
                @click="moveProvider(index, 1)"
              >
                <Icon icon="fa6-solid:chevron-down" class="h-3.5 w-3.5" />
              </button>
            </li>
          </ul>
          <p class="text-[11px] text-base-content/40 mt-1.5">
            {{ t('settings.audioSourceHint') }}
          </p>
        </div>

        <!-- slskd -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.slskdSection') }}
          </label>
          <p class="text-[11px] text-base-content/50 mb-3">
            {{ t('settings.slskdHint') }}
          </p>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.slskd.enabled"
              @change="onSlskdToggled"
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
            class="mt-2 grid grid-cols-1 gap-2"
          >
            <input
              type="url"
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              :placeholder="t('settings.slskdBaseUrl')"
              v-model.trim="sm.settings.value.slskd.base_url"
            />
            <input
              type="password"
              autocomplete="off"
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              :placeholder="t('settings.slskdApiKey')"
              v-model.trim="sm.settings.value.slskd.api_key"
            />
            <label class="text-xs text-base-content/50 mt-1">
              {{ t('settings.slskdSourceDir') }}
            </label>
            <input
              type="text"
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60 font-mono text-sm"
              placeholder="/slskd"
              v-model.trim="sm.settings.value.slskd.source_dir"
            />
            <p class="text-[11px] text-base-content/40">
              {{ t('settings.slskdSourceDirHint') }}
            </p>
            <label
              class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-sm checkbox-primary mt-0.5"
                v-model="sm.settings.value.slskd.leave_in_place"
              />
              <span class="flex-1 text-sm">
                <span class="block">{{ t('settings.slskdLeaveInPlace') }}</span>
                <span class="block text-[11px] text-base-content/50">
                  {{ t('settings.slskdLeaveInPlaceHint') }}
                </span>
              </span>
            </label>
            <div class="grid grid-cols-2 gap-2">
              <label class="text-xs text-base-content/50">
                {{ t('settings.slskdDownloadTimeout') }}
                <input
                  type="number"
                  inputmode="numeric"
                  min="30"
                  max="3600"
                  class="input input-sm w-full mt-1 rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
                  v-model.number="
                    sm.settings.value.slskd.download_timeout_seconds
                  "
                />
              </label>
              <label class="text-xs text-base-content/50">
                {{ t('settings.slskdQueuedTimeout') }}
                <input
                  type="number"
                  inputmode="numeric"
                  min="15"
                  max="3600"
                  class="input input-sm w-full mt-1 rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
                  v-model.number="
                    sm.settings.value.slskd.queued_timeout_seconds
                  "
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

        <!-- Filename template -->
        <div>
          <div class="flex items-baseline justify-between mb-2 gap-3">
            <label
              class="block text-xs font-semibold uppercase tracking-wider text-base-content/50"
            >
              {{ t('settings.outputTemplate') }}
            </label>
            <button
              type="button"
              class="text-[11px] text-primary hover:text-primary-focus transition-colors"
              @click="resetOutputTemplate"
            >
              {{ t('settings.outputTemplateReset') }}
            </button>
          </div>
          <input
            type="text"
            class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60 font-mono text-sm"
            v-model.trim="sm.settings.value.output"
            :placeholder="sm.settingsOptions.output"
          />
          <p class="text-[11px] text-base-content/40 mt-1.5">
            {{ t('settings.outputTemplateHint') }}
          </p>
        </div>

        <!-- Search -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.searchSection') }}
          </label>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.search_albums"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.searchAlbums') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.searchAlbumsHint') }}
              </span>
            </span>
          </label>
        </div>

        <!-- Playlists -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.playlistsSection') }}
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
              <span class="block">{{ t('settings.generateM3u') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.generateM3uHint') }}
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
          <p class="text-[11px] text-base-content/50 mb-3">
            {{ t('settings.navidromeHint') }}
          </p>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
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
            class="mt-2 grid grid-cols-1 gap-2"
          >
            <input
              type="url"
              class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              :placeholder="t('settings.navidromeUrl')"
              v-model.trim="sm.settings.value.navidrome.url"
            />
            <div class="grid grid-cols-2 gap-2">
              <input
                type="text"
                autocomplete="off"
                class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
                :placeholder="t('settings.navidromeUsername')"
                v-model.trim="sm.settings.value.navidrome.username"
              />
              <input
                type="password"
                autocomplete="off"
                class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
                :placeholder="t('settings.navidromePassword')"
                v-model="sm.settings.value.navidrome.password"
              />
              <input
                type="text"
                autocomplete="off"
                class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
                :placeholder="t('settings.navidromeAdminUsername')"
                v-model.trim="sm.settings.value.navidrome.admin_username"
              />
              <input
                type="password"
                autocomplete="off"
                class="input w-full rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
                :placeholder="t('settings.navidromeAdminPassword')"
                v-model="sm.settings.value.navidrome.admin_password"
              />
            </div>
            <p class="text-[11px] text-base-content/40">
              {{ t('settings.navidromeAdminHint') }}
            </p>
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
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20 mb-2"
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
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.organize_by_album"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.organizeByAlbum') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.organizeByAlbumHint') }}
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
              v-for="n in sm.settingsOptions.max_parallel_downloads_presets"
              :key="n"
              type="button"
              class="rounded-xl border px-2 py-2 text-sm font-medium transition-colors text-center"
              :class="[
                sm.settings.value.max_parallel_downloads === n
                  ? 'border-primary/50 bg-primary/10 text-primary'
                  : 'border-white/10 hover:border-white/20 hover:bg-white/5',
              ]"
              @click="setParallelDownloads(n)"
            >
              {{ n }}
            </button>
          </div>
          <div class="flex items-center gap-2 mt-2">
            <input
              type="number"
              inputmode="numeric"
              class="input input-sm w-24 rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              :min="sm.settingsOptions.max_parallel_downloads_min"
              :max="sm.settingsOptions.max_parallel_downloads_max"
              :value="sm.settings.value.max_parallel_downloads"
              @change="setParallelDownloads($event.target.value)"
            />
            <span class="text-[11px] text-base-content/40">
              {{
                t('settings.parallelDownloadsCustomHint', {
                  min: sm.settingsOptions.max_parallel_downloads_min,
                  max: sm.settingsOptions.max_parallel_downloads_max,
                })
              }}
            </span>
          </div>
          <p class="text-[11px] text-base-content/40 mt-1.5">
            {{ t('settings.parallelDownloadsHint') }}
          </p>
        </div>

        <!-- Download delay -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.downloadDelay') }}
          </label>
          <div class="grid grid-cols-5 gap-1.5">
            <button
              v-for="n in sm.settingsOptions.download_delay_seconds_presets"
              :key="n"
              type="button"
              class="rounded-xl border px-2 py-2 text-sm font-medium transition-colors text-center"
              :class="[
                sm.settings.value.download_delay_seconds === n
                  ? 'border-primary/50 bg-primary/10 text-primary'
                  : 'border-white/10 hover:border-white/20 hover:bg-white/5',
              ]"
              @click="setDownloadDelay(n)"
            >
              {{ n }}
            </button>
          </div>
          <div class="flex items-center gap-2 mt-2">
            <input
              type="number"
              inputmode="numeric"
              class="input input-sm w-24 rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
              :min="sm.settingsOptions.download_delay_seconds_min"
              :max="sm.settingsOptions.download_delay_seconds_max"
              :value="sm.settings.value.download_delay_seconds"
              @change="setDownloadDelay($event.target.value)"
            />
            <span class="text-[11px] text-base-content/40">
              {{
                t('settings.downloadDelayCustomHint', {
                  min: sm.settingsOptions.download_delay_seconds_min,
                  max: sm.settingsOptions.download_delay_seconds_max,
                })
              }}
            </span>
          </div>
          <p class="text-[11px] text-base-content/40 mt-1.5">
            {{ t('settings.downloadDelayHint') }}
          </p>
        </div>

        <!-- Cover art -->
        <div>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20 mb-3"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.download_cover_art"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.downloadCoverArt') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.downloadCoverArtHint') }}
              </span>
            </span>
          </label>

          <div
            :class="{
              'opacity-40 pointer-events-none':
                !sm.settings.value.download_cover_art,
            }"
          >
            <label
              class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
            >
              {{ t('settings.coverResolution') }}
            </label>
            <div class="grid grid-cols-5 gap-1.5">
              <button
                v-for="n in sm.settingsOptions.cover_resolution_presets"
                :key="n"
                type="button"
                :disabled="!sm.settings.value.download_cover_art"
                class="rounded-xl border px-2 py-2 text-sm font-medium transition-colors text-center"
                :class="[
                  sm.settings.value.cover_resolution === n
                    ? 'border-primary/50 bg-primary/10 text-primary'
                    : 'border-white/10 hover:border-white/20 hover:bg-white/5',
                ]"
                @click="setCoverResolution(n)"
              >
                {{ n }}
              </button>
            </div>
            <div class="flex items-center gap-3 mt-3">
              <input
                type="range"
                :min="sm.settingsOptions.cover_resolution_min"
                :max="sm.settingsOptions.cover_resolution_max"
                step="50"
                :disabled="!sm.settings.value.download_cover_art"
                :value="sm.settings.value.cover_resolution"
                @input="setCoverResolution($event.target.value)"
                class="range range-xs range-primary flex-1"
              />
              <span
                class="text-xs tabular-nums w-16 text-right shrink-0 text-base-content/60"
              >
                {{ sm.settings.value.cover_resolution }}px
              </span>
            </div>
            <p class="text-[11px] text-base-content/40 mt-1.5">
              {{ t('settings.coverResolutionHint') }}
            </p>
          </div>
        </div>

        <!-- Overwrite existing files -->
        <div>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.overwrite_existing_files"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{
                t('settings.overwriteExistingFiles')
              }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.overwriteExistingFilesHint') }}
              </span>
            </span>
          </label>
        </div>

        <!-- Mini player bar -->
        <div>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.mini_player_enabled"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.miniPlayer') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.miniPlayerHint') }}
              </span>
            </span>
          </label>
        </div>

        <!-- Library -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.librarySection') }}
          </label>
          <label
            class="flex items-start gap-3 rounded-xl border border-white/10 bg-base-100/85 px-3 py-2.5 cursor-pointer hover:border-white/20 mb-3"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm checkbox-primary mt-0.5"
              v-model="sm.settings.value.cache_cover_art"
            />
            <span class="flex-1 text-sm">
              <span class="block">{{ t('settings.cacheCoverArt') }}</span>
              <span class="block text-[11px] text-base-content/50">
                {{ t('settings.cacheCoverArtHint') }}
              </span>
            </span>
          </label>
          <p class="text-[11px] text-base-content/50 mb-2">
            {{ t('settings.reconcileHint') }}
          </p>
          <button
            type="button"
            class="btn btn-sm h-10 px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100 w-full"
            :disabled="reconcileBusy"
            @click="runReconcile"
          >
            <span
              v-if="reconcileBusy"
              class="loading loading-spinner loading-xs mr-2"
            />
            <Icon v-else icon="fa6-solid:arrows-rotate" class="h-4 w-4 mr-2" />
            {{ t('settings.reconcileButton') }}
          </button>
          <p
            v-if="reconcileMessage"
            class="text-[11px] mt-2"
            :class="reconcileError ? 'text-error' : 'text-primary'"
          >
            {{ reconcileMessage }}
          </p>
        </div>

        <!-- YouTube cookies -->
        <div>
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-2"
          >
            {{ t('settings.cookies') }}
          </label>
          <p class="text-[11px] text-base-content/50 mb-3">
            {{ t('settings.cookiesHint') }}
          </p>

          <!-- Managed by DOWNTIFY_COOKIES_FILE: read-only here -->
          <div
            v-if="cm.status.value.locked"
            class="surface rounded-xl p-3 flex gap-2 text-sm"
          >
            <Icon
              icon="fa6-solid:lock"
              class="h-4 w-4 shrink-0 mt-0.5 text-base-content/50"
            />
            <span class="flex-1 min-w-0">
              <span class="block">{{ t('settings.cookiesLocked') }}</span>
              <span
                class="block text-[11px] text-base-content/50 truncate"
                :title="cm.status.value.path"
              >
                {{ cm.status.value.path }}
              </span>
              <span
                v-if="!cm.status.value.configured"
                class="block text-[11px] text-error mt-1"
              >
                {{ t('settings.cookiesEnvMissing') }}
              </span>
            </span>
          </div>

          <template v-else>
            <div
              v-if="cm.status.value.configured"
              class="surface rounded-xl p-3 flex items-center gap-2 text-sm mb-2"
            >
              <Icon
                icon="fa6-solid:circle-check"
                class="h-4 w-4 shrink-0 text-primary"
              />
              <span class="flex-1 min-w-0">
                <span class="block">{{ t('settings.cookiesConfigured') }}</span>
                <span class="block text-[11px] text-base-content/50">
                  {{ formatCookieSize(cm.status.value.size) }}
                  <template v-if="cm.status.value.updated_at">
                    · {{ formatCookieDate(cm.status.value.updated_at) }}
                  </template>
                </span>
              </span>
              <button
                type="button"
                class="icon-btn text-error/70 hover:text-error hover:bg-error/10 shrink-0"
                :disabled="cm.busy.value"
                @click="onDeleteCookies"
                :title="t('settings.cookiesDelete')"
              >
                <span
                  v-if="cm.busy.value"
                  class="loading loading-spinner loading-xs"
                />
                <Icon v-else icon="fa6-solid:trash" class="h-4 w-4" />
              </button>
            </div>

            <label
              class="btn btn-sm h-10 px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100 cursor-pointer w-full"
              :class="{ 'pointer-events-none opacity-60': cm.busy.value }"
            >
              <span
                v-if="cm.busy.value"
                class="loading loading-spinner loading-xs mr-2"
              />
              <Icon
                v-else
                icon="fa6-solid:cloud-arrow-up"
                class="h-4 w-4 mr-2"
              />
              {{
                cm.status.value.configured
                  ? t('settings.cookiesReplace')
                  : t('settings.cookiesUpload')
              }}
              <input
                ref="cookiesInput"
                type="file"
                accept=".txt,text/plain"
                class="hidden"
                @change="onCookiesSelected"
              />
            </label>
          </template>

          <div
            v-if="cm.error.value"
            class="surface rounded-xl p-3 mt-2 flex gap-2 text-sm text-error"
          >
            <Icon
              icon="fa6-solid:circle-exclamation"
              class="h-4 w-4 shrink-0 mt-0.5"
            />
            <span class="flex-1">{{ cm.error.value }}</span>
          </div>
          <div
            v-for="warning in cm.warnings.value"
            :key="warning"
            class="surface rounded-xl p-3 mt-2 flex gap-2 text-sm text-warning"
          >
            <Icon
              icon="fa6-solid:triangle-exclamation"
              class="h-4 w-4 shrink-0 mt-0.5"
            />
            <span class="flex-1">{{ warning }}</span>
          </div>
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
            <Icon icon="fa6-solid:check" class="h-4 w-4 shrink-0" />
            {{ t('settings.saved') }}
          </div>
          <div
            v-else-if="sm.isSaved.value === false"
            class="surface rounded-xl p-3 flex items-center gap-2 text-sm text-error"
          >
            <Icon
              icon="fa6-solid:circle-exclamation"
              class="h-4 w-4 shrink-0"
            />
            {{ sm.saveErrorText.value || t('settings.saveError') }}
          </div>
        </transition>
      </div>

      <!-- Footer -->
      <div
        class="shrink-0 flex items-center justify-end gap-2 px-6 py-4 border-t border-white/5"
      >
        <label
          for="settings-modal"
          class="btn btn-sm h-10 px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100 cursor-pointer"
        >
          {{ t('common.cancel') }}
        </label>
        <button
          class="btn btn-primary btn-sm h-10 px-6 rounded-full"
          @click="saveSettings"
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
import { onMounted, ref } from 'vue'
import { Icon } from '@iconify/vue'
import {
  clampCoverResolution,
  clampDownloadDelaySeconds,
  clampParallelDownloads,
  useSettingsManager,
} from '../model/settings'
import { useCookiesManager } from '../model/cookies'
import API from '../model/api'
import { useI18n } from '../i18n'

const sm = useSettingsManager()
const cm = useCookiesManager()
const { t, locale, setLocale, locales } = useI18n()

const cookiesInput = ref(null)

onMounted(cm.refresh)

function formatCookieSize(bytes) {
  if (!bytes && bytes !== 0) return ''
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}

function formatCookieDate(iso) {
  const parsed = new Date(iso)
  return Number.isNaN(parsed.getTime()) ? '' : parsed.toLocaleString()
}

async function onCookiesSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  await cm.upload(file)
  // Reset so re-picking the same file still fires @change.
  if (cookiesInput.value) cookiesInput.value.value = ''
}

async function onDeleteCookies() {
  if (!confirm(t('settings.cookiesDeletePrompt'))) return
  await cm.remove()
}

function providerLabel(provider) {
  if (provider === 'youtube-music') return 'YouTube Music'
  if (provider === 'youtube') return 'YouTube'
  if (provider === 'slskd') return 'slskd'
  return provider
}

// audio_providers is an ordered fallback list: each track tries the
// providers in order until one yields audio.
function enabledProviders() {
  return (sm.settings.value.audio_providers || []).filter(Boolean)
}

function providerIndex(provider) {
  return enabledProviders().indexOf(provider)
}

function toggleProvider(provider) {
  const list = enabledProviders()
  const idx = list.indexOf(provider)
  if (idx >= 0) {
    if (list.length === 1) return // keep at least one source
    list.splice(idx, 1)
  } else {
    list.push(provider)
    if (provider === 'slskd') sm.settings.value.slskd.enabled = true
  }
  sm.settings.value.audio_providers = list
}

function moveProvider(index, delta) {
  const list = enabledProviders()
  const target = index + delta
  if (target < 0 || target >= list.length) return
  ;[list[index], list[target]] = [list[target], list[index]]
  sm.settings.value.audio_providers = list
}

function onSlskdToggled() {
  const list = enabledProviders()
  const idx = list.indexOf('slskd')
  if (sm.settings.value.slskd.enabled && idx < 0) {
    sm.settings.value.audio_providers = ['slskd', ...list]
  } else if (!sm.settings.value.slskd.enabled && idx >= 0) {
    list.splice(idx, 1)
    sm.settings.value.audio_providers = list.length ? list : ['youtube-music']
  }
}

const reconcileBusy = ref(false)
const reconcileMessage = ref('')
const reconcileError = ref(false)

async function runReconcile() {
  reconcileBusy.value = true
  reconcileMessage.value = ''
  reconcileError.value = false
  try {
    const { data } = await API.reconcileLibrary()
    const parts = []
    if (data.paths_updated) {
      parts.push(t('settings.reconcilePaths', { count: data.paths_updated }))
    }
    if (data.pruned_stale) {
      parts.push(t('settings.reconcilePruned', { count: data.pruned_stale }))
    }
    if (data.content_keys_backfilled) {
      parts.push(
        t('settings.reconcileIndexed', {
          count: data.content_keys_backfilled,
        })
      )
    }
    const refreshed = data.playlists_affected || []
    if (refreshed.length && (data.refresh_m3u || data.refresh_navidrome)) {
      parts.push(
        t('settings.reconcilePlaylists', { playlists: refreshed.join(', ') })
      )
    }
    reconcileMessage.value = parts.length
      ? parts.join(' ')
      : t('settings.reconcileNone')
  } catch {
    reconcileError.value = true
    reconcileMessage.value = t('settings.reconcileError')
  } finally {
    reconcileBusy.value = false
  }
}

function setParallelDownloads(value) {
  sm.settings.value.max_parallel_downloads = clampParallelDownloads(value)
}

function setDownloadDelay(value) {
  sm.settings.value.download_delay_seconds = clampDownloadDelaySeconds(value)
}

function setCoverResolution(value) {
  sm.settings.value.cover_resolution = clampCoverResolution(value)
}

function resetOutputTemplate() {
  sm.settings.value.output = sm.settingsOptions.output
}

function saveSettings() {
  if (!String(sm.settings.value.output || '').trim()) {
    resetOutputTemplate()
  }
  sm.saveSettings()
}
</script>
