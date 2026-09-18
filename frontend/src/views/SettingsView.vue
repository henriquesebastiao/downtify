<template>
  <div
    class="mx-auto flex max-w-[1280px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader
      :title="t('settings.title')"
      :subtitle="t('settings.subtitle')"
    />

    <div class="grid items-start gap-8 lg:grid-cols-[220px_minmax(0,1fr)]">
      <!-- Section navigation -->
      <nav
        class="-mx-4 flex gap-1 overflow-x-auto px-4 [scrollbar-width:none] lg:sticky lg:top-[96px] lg:mx-0 lg:flex-col lg:px-0"
        :aria-label="t('settings.sections')"
      >
        <RouterLink
          v-for="item in sections"
          :key="item.id"
          :to="{ name: 'Settings', params: { section: item.id } }"
          replace
          class="flex h-10 shrink-0 items-center gap-2.5 rounded-control px-3 text-sm whitespace-nowrap transition-colors"
          :class="
            section === item.id
              ? 'bg-surface-2 font-semibold text-fg'
              : 'font-medium text-muted hover:bg-surface-2/60 hover:text-fg'
          "
        >
          <AppIcon
            :name="item.icon"
            :size="17"
            :class="section === item.id ? 'text-accent' : ''"
          />
          {{ item.label }}
        </RouterLink>
      </nav>

      <div v-if="!sm.loaded.value" class="flex flex-col gap-3">
        <UiSkeleton v-for="n in 4" :key="n" class="h-20 !rounded-panel" />
      </div>

      <Transition v-else name="page" mode="out-in">
        <div :key="section" class="flex min-w-0 flex-col gap-8">
          <!-- General -->
          <template v-if="section === 'general'">
            <SettingGroup :title="t('settings.appearance')">
              <SettingRow
                :label="t('settings.theme')"
                :description="t('settings.themeHint')"
              >
                <UiSegmented
                  :model-value="theme.mode.value"
                  show-labels
                  :options="[
                    {
                      value: 'dark',
                      icon: 'moon',
                      label: t('settings.themeDark'),
                    },
                    {
                      value: 'light',
                      icon: 'sun',
                      label: t('settings.themeLight'),
                    },
                    {
                      value: 'system',
                      icon: 'monitor',
                      label: t('settings.themeSystem'),
                    },
                  ]"
                  @update:model-value="theme.setMode"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.language')"
                :description="t('settings.languageHint')"
              >
                <UiSelect
                  :model-value="locale"
                  :options="
                    locales.map((l) => ({ value: l.code, label: l.name }))
                  "
                  :label="t('settings.language')"
                  icon="globe"
                  @update:model-value="setLocale"
                />
              </SettingRow>
            </SettingGroup>
            <SettingGroup :title="t('settings.playerGroup')">
              <!-- Per device and applied at once, like the theme: it isn't
                   part of what "Save" sends to the server. -->
              <SettingRow
                :label="t('settings.showLyrics')"
                :description="t('settings.showLyricsHint')"
              >
                <UiSwitch
                  v-model="showLyrics"
                  :aria-label="t('settings.showLyrics')"
                />
              </SettingRow>
            </SettingGroup>
            <SettingGroup :title="t('settings.searchGroup')">
              <SettingRow
                :label="t('settings.searchAlbums')"
                :description="t('settings.searchAlbumsHint')"
              >
                <UiSwitch
                  v-model="s.search_albums"
                  :aria-label="t('settings.searchAlbums')"
                />
              </SettingRow>
            </SettingGroup>
            <SettingGroup :title="t('settings.shortcutsGroup')">
              <SettingRow
                :label="t('shortcuts.title')"
                :description="t('settings.shortcutsHint')"
              >
                <UiButton
                  variant="ghost"
                  icon="keyboard"
                  @click="openShortcuts"
                >
                  {{ t('settings.showShortcuts') }}
                </UiButton>
              </SettingRow>
            </SettingGroup>
          </template>

          <!-- Audio sources -->
          <template v-else-if="section === 'sources'">
            <SettingGroup
              :title="t('settings.sourcesTitle')"
              :description="t('settings.sourcesHint')"
            >
              <SourceOrder
                v-model="s.audio_providers"
                @enable-slskd="s.slskd.enabled = true"
              />
            </SettingGroup>

            <SettingGroup
              :title="t('settings.slskdTitle')"
              :description="t('settings.slskdHint')"
            >
              <SettingRow
                :label="t('settings.slskdEnabled')"
                :description="t('settings.slskdEnabledHint')"
              >
                <UiSwitch
                  v-model="s.slskd.enabled"
                  :aria-label="t('settings.slskdEnabled')"
                />
              </SettingRow>
              <template v-if="s.slskd.enabled">
                <div class="grid gap-4 px-5 py-4 sm:grid-cols-2">
                  <UiInput
                    v-model.trim="s.slskd.base_url"
                    :label="t('settings.slskdUrl')"
                    placeholder="http://slskd:5030"
                    type="url"
                    :error="needsValue(s.slskd.base_url)"
                  />
                  <UiInput
                    v-model.trim="s.slskd.api_key"
                    :label="t('settings.slskdKey')"
                    type="password"
                    :error="needsValue(s.slskd.api_key)"
                  />
                  <UiInput
                    v-model.trim="s.slskd.source_dir"
                    :label="t('settings.slskdFolder')"
                    :hint="t('settings.slskdFolderHint')"
                    placeholder="/slskd"
                    mono
                  />
                  <div class="grid grid-cols-2 gap-3">
                    <UiInput
                      v-model="s.slskd.download_timeout_seconds"
                      :label="t('settings.slskdTimeout')"
                      type="number"
                      min="30"
                      max="3600"
                      suffix="s"
                    />
                    <UiInput
                      v-model="s.slskd.queued_timeout_seconds"
                      :label="t('settings.slskdQueuedTimeout')"
                      type="number"
                      min="15"
                      max="3600"
                      suffix="s"
                    />
                  </div>
                </div>
                <div class="px-5 py-4">
                  <ConnectionTest
                    kind="slskd"
                    :config="s.slskd"
                    :url="s.slskd.base_url"
                  />
                </div>
                <SettingRow
                  :label="t('settings.slskdInPlace')"
                  :description="t('settings.slskdInPlaceHint')"
                >
                  <UiSwitch
                    v-model="s.slskd.leave_in_place"
                    :aria-label="t('settings.slskdInPlace')"
                  />
                </SettingRow>
              </template>
            </SettingGroup>

            <SettingGroup :title="t('settings.youtubeTitle')">
              <CookiesCard />
            </SettingGroup>
          </template>

          <!-- Downloads & files -->
          <template v-else-if="section === 'files'">
            <SettingGroup :title="t('settings.audioGroup')">
              <SettingRow
                :label="t('settings.format')"
                :description="t('settings.formatHint')"
              >
                <UiSegmented
                  v-model="s.format"
                  show-labels
                  :options="
                    sm.settingsOptions.format.map((f) => ({
                      value: f,
                      label: f.toUpperCase(),
                    }))
                  "
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.bitrate')"
                :description="
                  s.format === 'flac'
                    ? t('settings.bitrateLossless')
                    : t('settings.bitrateHint')
                "
              >
                <UiSegmented
                  v-model="s.bitrate"
                  show-labels
                  :class="
                    s.format === 'flac' ? 'pointer-events-none opacity-40' : ''
                  "
                  :options="
                    sm.settingsOptions.bitrate.map((b) => ({
                      value: b,
                      label: `${b}k`,
                    }))
                  "
                />
              </SettingRow>
            </SettingGroup>

            <SettingGroup :title="t('settings.filesGroup')">
              <SettingRow
                :label="t('settings.template')"
                :description="t('settings.templateHint')"
                stacked
              >
                <div class="flex w-full flex-col gap-2">
                  <div class="flex gap-2">
                    <UiInput
                      v-model.trim="s.output"
                      class="flex-1"
                      :placeholder="sm.settingsOptions.output"
                      mono
                    />
                    <UiButton
                      variant="ghost"
                      @click="s.output = sm.settingsOptions.output"
                    >
                      {{ t('settings.reset') }}
                    </UiButton>
                  </div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="token in templateTokens"
                      :key="token"
                      type="button"
                      class="rounded-md border border-line-3 bg-surface-2 px-2 py-1 font-mono text-xs text-fg-3 hover:border-accent hover:text-accent"
                      @click="addToken(token)"
                    >
                      {{ token }}
                    </button>
                  </div>
                  <p class="text-xs text-muted">
                    {{ t('settings.templatePreview') }}
                    <span class="font-mono text-fg-3">{{
                      templatePreview
                    }}</span>
                  </p>
                </div>
              </SettingRow>
              <SettingRow
                :label="t('settings.byArtist')"
                :description="t('settings.byArtistHint')"
              >
                <UiSwitch
                  v-model="s.organize_by_artist"
                  :aria-label="t('settings.byArtist')"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.byAlbum')"
                :description="t('settings.byAlbumHint')"
              >
                <UiSwitch
                  v-model="s.organize_by_album"
                  :aria-label="t('settings.byAlbum')"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.overwrite')"
                :description="t('settings.overwriteHint')"
              >
                <UiSwitch
                  v-model="s.overwrite_existing_files"
                  :aria-label="t('settings.overwrite')"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.m3u')"
                :description="t('settings.m3uHint')"
              >
                <UiSwitch
                  v-model="s.generate_m3u"
                  :aria-label="t('settings.m3u')"
                />
              </SettingRow>
              <!-- The cover is saved next to the .m3u, so it only has
                   somewhere to go while playlist files are written. -->
              <SettingRow
                v-if="s.generate_m3u"
                :label="t('settings.playlistCover')"
                :description="t('settings.playlistCoverHint')"
              >
                <UiSwitch
                  v-model="s.download_cover_art_playlists"
                  :aria-label="t('settings.playlistCover')"
                />
              </SettingRow>
            </SettingGroup>

            <SettingGroup :title="t('settings.pacingGroup')">
              <SettingRow
                :label="t('settings.parallel')"
                :description="t('settings.parallelHint')"
                stacked
              >
                <PresetPicker
                  :model-value="s.max_parallel_downloads"
                  :presets="sm.settingsOptions.max_parallel_downloads_presets"
                  :min="sm.settingsOptions.max_parallel_downloads_min"
                  :max="sm.settingsOptions.max_parallel_downloads_max"
                  :custom-label="t('settings.custom')"
                  @update:model-value="
                    (v) =>
                      (s.max_parallel_downloads = clampParallelDownloads(v))
                  "
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.delay')"
                :description="t('settings.delayHint')"
                stacked
              >
                <PresetPicker
                  :model-value="s.download_delay_seconds"
                  :presets="sm.settingsOptions.download_delay_seconds_presets"
                  :min="sm.settingsOptions.download_delay_seconds_min"
                  :max="sm.settingsOptions.download_delay_seconds_max"
                  unit="s"
                  :format="(v) => `${v}s`"
                  :custom-label="t('settings.custom')"
                  @update:model-value="
                    (v) =>
                      (s.download_delay_seconds = clampDownloadDelaySeconds(v))
                  "
                />
              </SettingRow>
            </SettingGroup>
          </template>

          <!-- Tags, art, lyrics -->
          <template v-else-if="section === 'tags'">
            <SettingGroup :title="t('settings.artGroup')">
              <SettingRow
                :label="t('settings.coverArt')"
                :description="t('settings.coverArtHint')"
              >
                <UiSwitch
                  v-model="s.download_cover_art"
                  :aria-label="t('settings.coverArt')"
                />
              </SettingRow>
              <SettingRow
                v-if="s.download_cover_art"
                :label="t('settings.coverSize')"
                :description="t('settings.coverSizeHint')"
                stacked
              >
                <PresetPicker
                  :model-value="s.cover_resolution"
                  :presets="sm.settingsOptions.cover_resolution_presets"
                  :min="sm.settingsOptions.cover_resolution_min"
                  :max="sm.settingsOptions.cover_resolution_max"
                  unit="px"
                  :custom-label="t('settings.custom')"
                  @update:model-value="
                    (v) => (s.cover_resolution = clampCoverResolution(v))
                  "
                />
              </SettingRow>
            </SettingGroup>
            <SettingGroup :title="t('settings.lyricsGroup')">
              <SettingRow
                :label="t('settings.lyrics')"
                :description="t('settings.lyricsHint')"
              >
                <UiSwitch
                  v-model="s.download_lyrics"
                  :aria-label="t('settings.lyrics')"
                />
              </SettingRow>
              <SettingRow
                v-if="s.download_lyrics"
                :label="t('settings.lyricsProviders')"
                :description="t('settings.lyricsProvidersHint')"
                stacked
              >
                <LyricsOrder
                  v-model="s.lyrics_providers"
                  class="-mx-4 w-full"
                />
              </SettingRow>
            </SettingGroup>
          </template>

          <!-- Navidrome -->
          <template v-else-if="section === 'navidrome'">
            <SettingGroup
              :title="t('settings.navidromeTitle')"
              :description="t('settings.navidromeHint')"
            >
              <SettingRow
                :label="t('settings.navidromeEnabled')"
                :description="t('settings.navidromeEnabledHint')"
              >
                <UiSwitch
                  v-model="s.navidrome.enabled"
                  :aria-label="t('settings.navidromeEnabled')"
                />
              </SettingRow>
              <template v-if="s.navidrome.enabled">
                <div class="grid gap-4 px-5 py-4 sm:grid-cols-2">
                  <UiInput
                    v-model.trim="s.navidrome.url"
                    class="sm:col-span-2"
                    :label="t('settings.navidromeUrl')"
                    placeholder="http://navidrome:4533"
                    type="url"
                    :error="needsValue(s.navidrome.url)"
                  />
                  <UiInput
                    v-model.trim="s.navidrome.username"
                    :label="t('settings.navidromeUser')"
                    autocomplete="username"
                    :error="needsValue(s.navidrome.username)"
                  />
                  <UiInput
                    v-model="s.navidrome.password"
                    :label="t('settings.navidromePassword')"
                    type="password"
                    autocomplete="current-password"
                    :error="needsValue(s.navidrome.password)"
                  />
                  <UiInput
                    v-model.trim="s.navidrome.admin_username"
                    :label="t('settings.navidromeAdminUser')"
                    :hint="t('settings.navidromeAdminHint')"
                  />
                  <UiInput
                    v-model="s.navidrome.admin_password"
                    :label="t('settings.navidromeAdminPassword')"
                    type="password"
                  />
                </div>
                <div class="px-5 py-4">
                  <ConnectionTest
                    kind="navidrome"
                    :config="s.navidrome"
                    :url="s.navidrome.url"
                  />
                </div>
                <SettingRow
                  :label="t('settings.navidromeSync')"
                  :description="t('settings.navidromeSyncHint')"
                >
                  <UiSwitch
                    v-model="s.sync_navidrome"
                    :aria-label="t('settings.navidromeSync')"
                  />
                </SettingRow>
                <SettingRow :label="t('settings.navidromePublic')">
                  <UiSwitch
                    v-model="s.navidrome.public_playlist"
                    :aria-label="t('settings.navidromePublic')"
                  />
                </SettingRow>
              </template>
            </SettingGroup>
          </template>

          <!-- Library -->
          <template v-else-if="section === 'library'">
            <SettingGroup :title="t('settings.libraryGroup')">
              <SettingRow
                :label="t('settings.coverCache')"
                :description="t('settings.coverCacheHint')"
              >
                <UiSwitch
                  v-model="s.cache_cover_art"
                  :aria-label="t('settings.coverCache')"
                />
              </SettingRow>
              <SettingRow
                :label="t('settings.reconcile')"
                :description="t('settings.reconcileHint')"
                stacked
              >
                <UiButton
                  variant="secondary"
                  icon="wand"
                  :loading="reconciling"
                  @click="reconcile"
                >
                  {{ t('settings.reconcileButton') }}
                </UiButton>
                <p
                  v-if="reconcileResult"
                  class="text-[13px]"
                  :class="reconcileFailed ? 'text-danger' : 'text-accent'"
                >
                  {{ reconcileResult }}
                </p>
              </SettingRow>
            </SettingGroup>
          </template>

          <!-- About -->
          <template v-else-if="section === 'about'">
            <div
              class="flex items-center gap-4 rounded-panel border border-line-2 bg-surface p-6"
            >
              <AppLogo :size="56" />
              <div class="min-w-0">
                <p class="text-display text-2xl font-bold">Downtify</p>
                <p class="tabular text-sm text-muted">
                  {{ t('settings.version', { version: version || '—' }) }}
                </p>
              </div>
              <UiButton
                v-if="update?.update_available"
                variant="primary"
                icon="sparkle"
                class="ml-auto"
                :href="update.release_url"
              >
                {{
                  t('nav.updateAvailable', { version: update.latest_version })
                }}
              </UiButton>
              <UiBadge
                v-else-if="update"
                tone="accent"
                icon="check"
                class="ml-auto"
              >
                {{ t('settings.upToDate') }}
              </UiBadge>
            </div>
            <SettingGroup>
              <SettingRow
                :label="t('settings.source')"
                :description="t('settings.sourceHint')"
              >
                <UiButton
                  variant="ghost"
                  icon="arrow-up-right"
                  href="https://github.com/henriquesebastiao/downtify"
                >
                  GitHub
                </UiButton>
              </SettingRow>
              <SettingRow
                :label="t('settings.docs')"
                :description="t('settings.docsHint')"
              >
                <UiButton
                  variant="ghost"
                  icon="arrow-up-right"
                  href="https://henriquesebastiao.github.io/downtify/"
                >
                  {{ t('settings.openDocs') }}
                </UiButton>
              </SettingRow>
            </SettingGroup>
          </template>
        </div>
      </Transition>
    </div>

    <!-- Save bar -->
    <Transition name="now-playing">
      <div
        v-if="sm.dirty.value || sm.saveErrorText.value"
        class="sticky z-30 mx-auto flex w-full max-w-2xl flex-wrap items-center gap-3 rounded-panel border border-line-3 bg-surface-2/95 py-3 pr-3 pl-5 shadow-float backdrop-blur-xl"
        :class="
          hasTrack
            ? 'bottom-[calc(10rem+env(safe-area-inset-bottom))] md:bottom-28'
            : 'bottom-[calc(5.75rem+env(safe-area-inset-bottom))] md:bottom-6'
        "
        role="status"
      >
        <p
          class="min-w-0 flex-1 text-sm"
          :class="sm.saveErrorText.value ? 'text-danger' : 'text-fg-2'"
        >
          {{ sm.saveErrorText.value || t('settings.unsaved') }}
        </p>
        <UiButton
          variant="plain"
          :disabled="sm.saving.value"
          @click="discard"
          >{{ t('settings.discard') }}</UiButton
        >
        <UiButton
          variant="primary"
          icon="check"
          :loading="sm.saving.value"
          @click="save"
        >
          {{ t('settings.save') }}
        </UiButton>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import AppLogo from '/src/components/ui/AppLogo.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import CookiesCard from '/src/components/settings/CookiesCard.vue'
import ConnectionTest from '/src/components/settings/ConnectionTest.vue'
import PresetPicker from '/src/components/settings/PresetPicker.vue'
import SettingGroup from '/src/components/settings/SettingGroup.vue'
import SettingRow from '/src/components/settings/SettingRow.vue'
import SourceOrder from '/src/components/settings/SourceOrder.vue'
import LyricsOrder from '/src/components/settings/LyricsOrder.vue'
import API from '/src/model/api'
import {
  clampCoverResolution,
  clampDownloadDelaySeconds,
  clampParallelDownloads,
  useSettingsManager,
} from '/src/model/settings'
import { usePlayer } from '/src/model/player'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useTheme } from '/src/model/theme'
import { useUi } from '/src/model/ui'
import { useUpdateCheck } from '/src/model/updateCheck'
import { useI18n } from '/src/i18n'

const { t, locale, setLocale, locales } = useI18n()
const route = useRoute()
const sm = useSettingsManager()
const theme = useTheme()
const { showLyrics } = usePlayerPrefs()
const ui = useUi()
const player = usePlayer()
const update = useUpdateCheck().status

const hasTrack = computed(() => !!player.currentTrack.value)
const s = sm.settings
const version = localStorage.getItem('version')

const sections = computed(() => [
  { id: 'general', icon: 'sliders', label: t('settings.general') },
  { id: 'sources', icon: 'download', label: t('settings.sources') },
  { id: 'files', icon: 'folder', label: t('settings.files') },
  { id: 'tags', icon: 'tag', label: t('settings.tags') },
  { id: 'navidrome', icon: 'server', label: 'Navidrome' },
  { id: 'library', icon: 'library', label: t('settings.library') },
  { id: 'about', icon: 'info', label: t('settings.about') },
])

const section = computed(() => {
  const requested = String(route.params.section || '')
  return sections.value.some((item) => item.id === requested)
    ? requested
    : 'general'
})

function needsValue(value) {
  return String(value ?? '').trim() ? '' : t('settings.required')
}

const templateTokens = [
  '{artists}',
  '{artist}',
  '{title}',
  '{album}',
  '{tracknumber}',
  '/',
]

function addToken(token) {
  const current = String(s.value.output || sm.settingsOptions.output)
  const extIndex = current.lastIndexOf('.{output-ext}')
  const base = extIndex >= 0 ? current.slice(0, extIndex) : current
  const sep = token === '/' || base.endsWith('/') ? '' : ' - '
  s.value.output = `${base}${base ? sep : ''}${token}.{output-ext}`
}

const templatePreview = computed(() => {
  const template = String(s.value.output || sm.settingsOptions.output)
  const values = {
    '{artists}': 'Kenji Aoki, Mira Kovač',
    '{artist}': 'Kenji Aoki',
    '{title}': 'Harbor Lights',
    '{album}': 'Glass Harbor',
    '{tracknumber}': '01',
    '{output-ext}': s.value.format || 'mp3',
  }
  return Object.entries(values).reduce(
    (text, [token, value]) => text.split(token).join(value),
    template
  )
})

async function save() {
  if (!String(s.value.output || '').trim())
    s.value.output = sm.settingsOptions.output
  const ok = await sm.saveSettings()
  if (ok) ui.toast(t('settings.saved'), { kind: 'success' })
}

function discard() {
  sm.reset()
  sm.saveErrorText.value = ''
}

function openShortcuts() {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: '?' }))
}

const reconciling = ref(false)
const reconcileResult = ref('')
const reconcileFailed = ref(false)

async function reconcile() {
  reconciling.value = true
  reconcileResult.value = ''
  reconcileFailed.value = false
  try {
    const { data } = await API.reconcileLibrary()
    const parts = []
    if (data.paths_updated)
      parts.push(t('settings.reconcilePaths', { count: data.paths_updated }))
    if (data.pruned_stale)
      parts.push(t('settings.reconcilePruned', { count: data.pruned_stale }))
    if (data.content_keys_backfilled) {
      parts.push(
        t('settings.reconcileIndexed', { count: data.content_keys_backfilled })
      )
    }
    const refreshed = data.playlists_affected || []
    if (refreshed.length && (data.refresh_m3u || data.refresh_navidrome)) {
      parts.push(
        t('settings.reconcilePlaylists', { playlists: refreshed.join(', ') })
      )
    }
    reconcileResult.value = parts.length
      ? parts.join(' ')
      : t('settings.reconcileNone')
  } catch {
    reconcileFailed.value = true
    reconcileResult.value = t('settings.reconcileError')
  } finally {
    reconciling.value = false
  }
}

onBeforeRouteLeave(async (to) => {
  if (!sm.dirty.value || to.name === 'Settings') return true
  const leave = await ui.confirm({
    title: t('settings.leaveTitle'),
    body: t('settings.leaveBody'),
    confirmLabel: t('settings.discard'),
    danger: true,
  })
  if (leave) sm.reset()
  return leave
})
</script>
