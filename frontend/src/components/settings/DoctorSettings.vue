<template>
  <div class="flex flex-col gap-8">
    <SettingGroup :title="t('doctor.title')" :description="t('doctor.intro')">
      <SettingRow
        :label="t('doctor.checkup')"
        :description="
          health
            ? t('doctor.lastCheckup', { when: formatDate(health.scanned_at) })
            : t('doctor.checkupHint')
        "
      >
        <UiButton
          variant="primary"
          icon="stethoscope"
          :loading="runningKind === 'health'"
          :disabled="busy"
          @click="runHealth"
        >
          {{ t('doctor.runCheckup') }}
        </UiButton>
      </SettingRow>
      <div v-if="busy" class="flex flex-col gap-2 px-5 py-4">
        <div class="flex items-center justify-between gap-3 text-[13px]">
          <span class="text-fg-3">{{ stepLabel }}</span>
          <span v-if="progress.total" class="tabular text-muted">
            {{ progress.done }} / {{ progress.total }}
          </span>
        </div>
        <UiProgress
          :value="progress.total ? progress.done / progress.total : 0"
          :indeterminate="!progress.total"
        />
        <div v-if="job?.kind === 'slskd' || job?.kind === 'convert'">
          <UiButton variant="ghost" size="sm" @click="cancelJob">
            {{ t('doctor.stop') }}
          </UiButton>
        </div>
      </div>
      <p v-if="jobError" class="px-5 py-3 text-[13px] text-danger">
        {{ jobError }}
      </p>
    </SettingGroup>

    <div class="flex flex-col gap-3">
      <!-- An AI assistant that looks at the findings with you -->
      <AiHelper :busy="busy" :stale="stale" @applied="refresh" />

      <!-- slskd leftovers -->
      <DoctorSection
        id="slskd"
        :title="t('doctor.slskdTitle')"
        :description="t('doctor.slskdHint')"
        :status="slskdBadge.text"
        :status-tone="slskdBadge.tone"
        :stale="slskdStale"
        :busy="busy"
        @recheck="runSlskdScan"
      >
        <SettingRow
          :label="t('doctor.slskdLeftovers')"
          :description="slskdSummaryText"
        >
          <UiButton
            icon="search"
            :loading="runningKind === 'slskd'"
            :disabled="busy || health?.slskd?.in_place"
            @click="runSlskdScan"
          >
            {{ t('doctor.slskdCheck') }}
          </UiButton>
        </SettingRow>
        <SlskdFolderBreakdown
          v-if="health?.slskd?.folder"
          :folder="health.slskd.folder"
        />
        <div
          v-if="holdingQueue"
          class="flex flex-wrap items-center justify-between gap-3 bg-warn/8 px-5 py-3 text-[13px] text-warn"
        >
          <span>{{ t('doctor.queueHeld') }}</span>
          <UiButton variant="ghost" size="sm" @click="releaseSlskd">
            {{ t('doctor.slskdKeepResume') }}
          </UiButton>
        </div>
        <template v-if="slskd">
          <div class="flex flex-wrap gap-2 px-5 py-4">
            <UiBadge
              v-for="(bucket, status) in slskd.summary"
              :key="status"
              :tone="status === 'verified' ? 'accent' : 'neutral'"
            >
              {{ t(`doctor.status.${status}`) }} · {{ bucket.files }} ·
              {{ formatBytes(bucket.bytes) }}
            </UiBadge>
          </div>
          <div v-if="verifiedFiles.length" class="px-5 pb-4">
            <p class="mb-2 text-[13px] text-muted">
              {{ t('doctor.slskdVerifiedHint') }}
            </p>
            <ul class="flex flex-col gap-1.5 text-[13px]">
              <li
                v-for="file in verifiedFiles"
                :key="file.file"
                class="flex items-center gap-3 rounded-control bg-surface-2 px-3 py-2"
              >
                <DoctorCover
                  :file="file.match || file.file"
                  :name="file.title"
                  size="sm"
                />
                <span class="flex min-w-0 flex-1 flex-col">
                  <span class="truncate text-fg">{{ file.file }}</span>
                  <span class="truncate text-muted">
                    = {{ file.match }} · {{ formatBytes(file.bytes) }}
                  </span>
                </span>
              </li>
            </ul>
            <UiButton
              v-if="verifiedTotal > verifiedFiles.length"
              class="mt-2"
              variant="plain"
              size="sm"
              @click="loadVerified(verifiedFiles.length)"
            >
              {{ t('doctor.showMore') }}
            </UiButton>
          </div>
          <div class="flex flex-wrap gap-2 px-5 py-4">
            <UiButton
              variant="danger"
              icon="trash"
              :disabled="busy || !verifiedCount || slskdStale"
              @click="cleanSlskd"
            >
              {{
                t('doctor.slskdDelete', {
                  files: verifiedCount,
                  size: formatBytes(verifiedBytes),
                })
              }}
            </UiButton>
            <UiButton variant="ghost" :disabled="busy" @click="releaseSlskd">
              {{ t('doctor.slskdKeepResume') }}
            </UiButton>
          </div>
        </template>
        <div v-if="cleaned" class="flex flex-col gap-1 px-5 py-4 text-[13px]">
          <p class="text-fg">
            {{
              t('doctor.slskdCleaned', {
                files: cleaned.deleted,
                size: formatBytes(cleaned.bytes),
              })
            }}
          </p>
          <CheckLine
            :ok="cleaned.verified_gone"
            :text="t('doctor.checkGone')"
          />
          <CheckLine
            :ok="!cleaned.queue?.paused"
            :text="t('doctor.checkQueueResumed')"
          />
          <CheckLine
            v-if="cleaned.navidrome?.enabled"
            :ok="cleaned.navidrome.scan_complete"
            :text="t('doctor.checkNavidromeScan')"
          />
          <p v-if="cleaned.kept?.length" class="text-muted">
            {{ t('doctor.slskdKeptChanged', { files: cleaned.kept.length }) }}
          </p>
        </div>
      </DoctorSection>

      <!-- Files in formats the user doesn't want, converted to MP3 -->
      <FormatsSection
        :found="formatsFound"
        :converted="formatsConverted"
        :busy="busy"
        :running-kind="runningKind"
        :stale="isStale('formats')"
        @scan="runFormatsScan"
        @convert="convertFormats"
      />

      <template v-if="health">
        <!-- Playlists -->
        <DoctorSection
          id="playlists"
          :title="t('doctor.playlistsTitle')"
          :description="t('doctor.playlistsHint')"
          :status="countBadge(health.playlists.groups.length, 'toMerge')"
          :status-tone="health.playlists.groups.length ? 'warn' : 'accent'"
          :stale="isStale('playlists')"
          :busy="busy"
          @recheck="runHealth"
        >
          <div
            v-if="!health.playlists.groups.length"
            class="px-5 py-4 text-[13px] text-muted"
          >
            <CheckLine :ok="true" :text="t('doctor.playlistsOk')" />
          </div>
          <div
            v-if="health.playlists.groups.length"
            class="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
          >
            <UiSegmented
              v-model="playlistKind"
              :options="playlistKindOptions"
              show-labels
              :aria-label="t('doctor.kindLabel')"
            />
            <p class="text-[13px] text-muted">{{ t('doctor.decideHint') }}</p>
          </div>
          <PlaylistGroupCard
            v-for="group in visiblePlaylistGroups"
            :key="group.id"
            :group="group"
            :busy="busy || isStale('playlists')"
            :cover-version="health.scanned_at"
            decidable
            :decision="decisions[group.id] || ''"
            @decide="(value) => setDecision(group.id, value)"
          />
          <div
            v-if="decidedCount"
            class="sticky bottom-0 z-10 flex flex-wrap items-center justify-between gap-3 border-t border-line-2 bg-surface/95 px-5 py-3 backdrop-blur"
          >
            <p class="text-[13px] text-fg">
              {{
                t('doctor.applyCounts', {
                  merge: decidedMerge.length,
                  apart: decidedApart.length,
                })
              }}
            </p>
            <div class="flex gap-2">
              <UiButton variant="ghost" size="sm" @click="clearDecisions">
                {{ t('doctor.clearChoices') }}
              </UiButton>
              <UiButton
                variant="primary"
                size="sm"
                icon="check"
                :disabled="busy || isStale('playlists')"
                @click="applyDecisions"
              >
                {{ t('doctor.applyChanges') }}
              </UiButton>
            </div>
          </div>
          <div v-if="applied" class="flex flex-col gap-1 px-5 py-4 text-[13px]">
            <CheckLine
              :ok="!applied.failed?.length"
              :text="
                t('doctor.appliedMerged', {
                  count: applied.merged?.length || 0,
                })
              "
            />
            <p v-if="applied.apart" class="text-muted">
              {{ t('doctor.appliedApart', { count: applied.apart }) }}
            </p>
            <p v-if="applied.failed?.length" class="text-warn">
              {{
                t('doctor.appliedFailed', {
                  names: applied.failed.map((f) => f.keeper).join(', '),
                })
              }}
            </p>
            <CheckLine
              v-if="applied.others_gone !== undefined"
              :ok="applied.others_gone"
              :text="t('doctor.checkOthersGone')"
            />
            <CheckLine
              v-if="applied.navidrome?.enabled"
              :ok="applied.navidrome.scan_complete"
              :text="t('doctor.checkNavidromeScan')"
            />
            <p v-if="applied.backup" class="text-muted">
              {{ t('doctor.backupAt', { path: applied.backup }) }}
            </p>
          </div>
          <SettingRow
            v-if="health.playlists.kept_apart"
            :label="
              t('doctor.playlistsKeptApart', {
                count: health.playlists.kept_apart,
              })
            "
          >
            <UiButton
              size="sm"
              variant="ghost"
              :disabled="busy"
              @click="listPlaylistsAgain"
            >
              {{ t('doctor.dupeListAgain') }}
            </UiButton>
          </SettingRow>
          <div class="flex flex-col gap-3 px-5 py-4">
            <p class="text-sm font-semibold text-fg">
              {{ t('doctor.manualTitle') }}
            </p>
            <p class="text-[13px] text-muted">{{ t('doctor.manualHint') }}</p>
            <UiInput
              v-model.trim="filter"
              :placeholder="t('doctor.manualFilter')"
              icon="search"
            />
            <ul
              class="flex max-h-72 flex-col gap-1 overflow-y-auto text-[13px]"
            >
              <li v-for="item in filteredM3us" :key="item.path">
                <label
                  class="flex cursor-pointer items-center gap-2 rounded-control px-2 py-1.5 hover:bg-surface-2"
                >
                  <input
                    v-model="picked"
                    type="checkbox"
                    :value="item.path"
                    :disabled="item.manual"
                  />
                  <span class="min-w-0 flex-1 truncate">{{ item.path }}</span>
                  <span class="tabular text-muted">{{ item.songs }}</span>
                  <img
                    v-if="item.cover"
                    :src="coverOf(item.path, health.scanned_at)"
                    :alt="t('doctor.hasCover')"
                    :title="t('doctor.hasCover')"
                    loading="lazy"
                    class="size-6 shrink-0 rounded-[3px] object-cover"
                  />
                </label>
              </li>
            </ul>
            <div>
              <UiButton
                :disabled="picked.length < 2 || busy || isStale('playlists')"
                @click="preview"
              >
                {{ t('doctor.manualCompare') }}
              </UiButton>
            </div>
            <PlaylistGroupCard
              v-if="manualGroup"
              :group="manualGroup"
              :busy="busy || isStale('playlists')"
              :cover-version="health.scanned_at"
              @merge="mergePlaylists"
            />
          </div>
          <div v-if="merged" class="flex flex-col gap-1 px-5 py-4 text-[13px]">
            <p class="text-fg">
              {{
                t('doctor.merged', {
                  path: merged.keeper,
                  songs: merged.songs,
                })
              }}
            </p>
            <CheckLine
              :ok="merged.check.others_gone"
              :text="t('doctor.checkOthersGone')"
            />
            <CheckLine
              :ok="merged.check.keeper_cover"
              :text="t('doctor.checkCover')"
            />
            <CheckLine
              v-if="merged.navidrome?.enabled"
              :ok="merged.navidrome.now?.length === 1"
              :text="
                t('doctor.checkNavidromeOne', {
                  count: merged.navidrome.now?.length || 0,
                })
              "
            />
            <p class="text-muted">
              {{ t('doctor.backupAt', { path: merged.backup }) }}
            </p>
          </div>
        </DoctorSection>

        <!-- Navidrome -->
        <DoctorSection
          id="navidrome"
          title="Navidrome"
          :description="t('doctor.navidromeHint')"
          :status="navidromeBadge.text"
          :status-tone="navidromeBadge.tone"
          :stale="isStale('navidrome')"
          :busy="busy"
          @recheck="runHealth"
        >
          <div
            v-if="!nd.enabled || nd.reachable === false"
            class="px-5 py-4 text-[13px] text-muted"
          >
            {{
              nd.enabled ? t('doctor.navidromeDown') : t('doctor.navidromeOff')
            }}
          </div>
          <template v-else>
            <div v-if="!nd.native" class="px-5 py-3 text-[13px] text-warn">
              {{ t('doctor.navidromeNoAdmin') }}
            </div>
            <SettingRow
              :label="t('doctor.navidromeSummary')"
              :description="
                t('doctor.navidromeCounts', {
                  duplicates: nd.duplicates.length,
                  orphans: nd.orphans.length,
                  incomplete: nd.incomplete.length,
                })
              "
            >
              <UiButton
                variant="primary"
                icon="check"
                :disabled="
                  busy || !navidromePlan.delete.length || isStale('navidrome')
                "
                @click="repairNavidrome"
              >
                {{ t('doctor.navidromeFix') }}
              </UiButton>
            </SettingRow>
            <div
              v-if="nd.suggest_m3u_import"
              class="px-5 py-3 text-[13px] text-fg-3"
            >
              {{ t('doctor.navidromeSuggestImport') }}
            </div>
            <ul
              v-if="nd.duplicates.length || nd.orphans.length"
              class="flex flex-col gap-2 px-5 py-4 text-[13px]"
            >
              <li
                v-for="dup in nd.duplicates"
                :key="dup.id"
                class="rounded-control bg-surface-2 px-3 py-2"
              >
                <p class="font-semibold text-fg">
                  {{ dup.name }}
                  <UiBadge tone="warn" class="ml-1">
                    {{ t(`doctor.reason.${dup.reason}`) }}
                  </UiBadge>
                </p>
                <p
                  v-for="member in dup.members"
                  :key="member.id"
                  class="mt-1 flex flex-wrap items-center gap-x-2 text-muted"
                >
                  <DoctorCover
                    :m3u="member.m3u_exists ? member.m3u : ''"
                    :name="member.name"
                    :version="health.scanned_at"
                    size="sm"
                  />
                  <span>{{ t(`doctor.kind.${member.kind}`) }}</span>
                  <span class="tabular">· {{ member.songs }}</span>
                  <span v-if="member.owner">· {{ member.owner }}</span>
                  <span
                    v-if="navidromePlan.delete.includes(member.id)"
                    class="text-danger"
                    >· {{ t('doctor.willRemove') }}</span
                  >
                  <span
                    v-else-if="navidromePlan.blocked.includes(member.id)"
                    class="text-warn"
                    >· {{ t('doctor.wouldLoseSongs') }}</span
                  >
                </p>
              </li>
              <li
                v-for="orphan in nd.orphans"
                :key="orphan.id"
                class="rounded-control bg-surface-2 px-3 py-2"
              >
                <p class="font-semibold text-fg">
                  {{ orphan.name }}
                  <UiBadge tone="warn" class="ml-1">
                    {{ t('doctor.reason.orphan') }}
                  </UiBadge>
                </p>
                <p class="mt-1 text-muted">{{ orphan.m3u }}</p>
              </li>
            </ul>
            <ul
              v-if="nd.incomplete.length"
              class="flex flex-col gap-2 px-5 py-4 text-[13px]"
            >
              <li
                v-for="gap in nd.incomplete"
                :key="gap.id"
                class="rounded-control bg-surface-2 px-3 py-2"
              >
                <p class="font-semibold text-fg">{{ gap.name }}</p>
                <p class="text-muted">
                  {{
                    t('doctor.incomplete', {
                      songs: gap.songs,
                      m3u: gap.m3u_songs,
                    })
                  }}
                  <template v-if="gap.outside">
                    {{ t('doctor.incompleteOutside', { count: gap.outside }) }}
                  </template>
                </p>
              </li>
            </ul>
            <SettingRow
              :label="t('doctor.navidromeSongDupes')"
              :description="
                t('doctor.songDupesCounts', {
                  groups: nd.song_duplicates.groups,
                  extra: nd.song_duplicates.extra_copies,
                  slskd: nd.song_duplicates.slskd_copies,
                })
              "
            />
            <div
              v-if="ndResult"
              class="flex flex-col gap-1 px-5 py-4 text-[13px]"
            >
              <CheckLine
                :ok="!ndResult.still_listed.length && !ndResult.failed.length"
                :text="
                  t('doctor.ndRemoved', { count: ndResult.deleted.length })
                "
              />
              <CheckLine
                :ok="ndResult.scan_complete"
                :text="t('doctor.checkNavidromeScan')"
              />
              <CheckLine
                :ok="!ndResult.remaining.duplicates"
                :text="
                  t('doctor.ndRemaining', {
                    duplicates: ndResult.remaining.duplicates,
                    orphans: ndResult.remaining.orphans,
                  })
                "
              />
            </div>
          </template>
        </DoctorSection>

        <!-- Duplicate songs (Downtify) -->
        <DoctorSection
          id="duplicates"
          :title="t('doctor.duplicatesTitle')"
          :description="t('doctor.duplicatesHint')"
          :status="countBadge(health.duplicates.groups.length, 'toReview')"
          :status-tone="health.duplicates.groups.length ? 'warn' : 'accent'"
          :stale="isStale('duplicates')"
          :busy="busy"
          @recheck="runHealth"
        >
          <SettingRow
            :label="t('doctor.duplicatesExact')"
            :description="dupeText('exact')"
          />
          <SettingRow
            :label="t('doctor.duplicatesLikely')"
            :description="dupeText('likely')"
          />
          <div
            v-if="deduped"
            class="flex flex-col gap-1.5 px-5 py-4 text-[13px]"
          >
            <p class="text-fg">
              {{
                t('doctor.dupeMerged', {
                  keep: deduped.kept,
                  count: deduped.removed.length,
                })
              }}
            </p>
            <p v-if="deduped.playlists.length" class="text-muted">
              {{
                t('doctor.dupeMergedPlaylists', {
                  playlists: deduped.playlists.join(', '),
                })
              }}
            </p>
            <CheckLine
              :ok="!deduped.leftovers.length"
              :text="
                deduped.leftovers.length
                  ? t('doctor.dupeLeftovers', {
                      where: deduped.leftovers.join(', '),
                    })
                  : t('doctor.dupeCheckClean')
              "
            />
            <p v-if="deduped.failed.length" class="text-warn">
              {{
                t('doctor.dupeFailed', {
                  files: deduped.failed.map((f) => f.file).join(', '),
                })
              }}
            </p>
          </div>
          <DuplicateGroupCard
            v-for="group in health.duplicates.groups.slice(0, dupesShown)"
            :key="group.files.map((f) => f.file).join('|')"
            :group="group"
            :busy="busy || isStale('duplicates')"
            @merge="mergeDuplicates"
            @keep-all="keepAllDuplicates"
          />
          <div
            v-if="health.duplicates.groups.length > dupesShown"
            class="px-5 pb-4"
          >
            <UiButton variant="plain" size="sm" @click="dupesShown += 10">
              {{ t('doctor.showMore') }}
            </UiButton>
          </div>
          <SettingRow
            v-if="health.duplicates.kept_apart"
            :label="
              t('doctor.dupeKeptApart', { count: health.duplicates.kept_apart })
            "
          >
            <UiButton
              size="sm"
              variant="ghost"
              :disabled="busy"
              @click="listKeptAgain"
            >
              {{ t('doctor.dupeListAgain') }}
            </UiButton>
          </SettingRow>
        </DoctorSection>

        <!-- Repeat downloads -->
        <DoctorSection
          id="relinked"
          :title="t('doctor.relinkedTitle')"
          :description="t('doctor.relinkedHint')"
          :status="countBadge(health.relinked.songs, 'songsFound')"
          :status-tone="health.relinked.songs ? 'warn' : 'accent'"
          :stale="isStale('relinked')"
          :busy="busy"
          @recheck="runHealth"
        >
          <SettingRow
            :label="t('doctor.relinkedLabel')"
            :description="
              t('doctor.relinkedCounts', {
                songs: health.relinked.songs,
                extra: health.relinked.extra_files,
              })
            "
          />
          <ul
            v-if="health.relinked.examples.length"
            class="flex flex-col gap-1.5 px-5 py-4 text-[13px]"
          >
            <li
              v-for="item in health.relinked.examples.slice(0, 10)"
              :key="item.playlist + item.files[0]"
              class="flex items-start gap-3 rounded-control bg-surface-2 px-3 py-2"
            >
              <DoctorCover :file="item.files[0]" :name="item.title" size="sm" />
              <span class="flex min-w-0 flex-1 flex-col">
                <span class="text-fg">
                  {{ item.artist }} — {{ item.title }}
                  <span class="text-muted">· {{ item.playlist }}</span>
                </span>
                <span
                  v-for="file in item.files"
                  :key="file"
                  class="truncate text-muted"
                >
                  {{ file }}
                </span>
              </span>
            </li>
          </ul>
        </DoctorSection>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import API from '/src/model/api'
import { useI18n } from '/src/i18n'
import { useUi } from '/src/model/ui'
import { formatBytes } from '/src/lib/format'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiProgress from '/src/components/ui/UiProgress.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import SettingGroup from '/src/components/settings/SettingGroup.vue'
import SettingRow from '/src/components/settings/SettingRow.vue'
import CheckLine from '/src/components/settings/doctor/CheckLine.vue'
import DoctorSection from '/src/components/settings/doctor/DoctorSection.vue'
import DoctorCover from '/src/components/settings/doctor/DoctorCover.vue'
import AiHelper from '/src/components/settings/doctor/AiHelper.vue'
import FormatsSection from '/src/components/settings/doctor/FormatsSection.vue'
import SlskdFolderBreakdown from '/src/components/settings/doctor/SlskdFolderBreakdown.vue'
import { playlistCoverOf } from '/src/components/settings/doctor/covers'
import PlaylistGroupCard from '/src/components/settings/doctor/PlaylistGroupCard.vue'
import DuplicateGroupCard from '/src/components/settings/doctor/DuplicateGroupCard.vue'

const { t, locale } = useI18n()
const ui = useUi()

const job = ref(null)
const jobError = ref('')
const health = ref(null)
const slskd = ref(null)
const cleaned = ref(null)
const merged = ref(null)
const ndResult = ref(null)
const deduped = ref(null)
const formatsFound = ref(null)
const formatsConverted = ref(null)
const holdingQueue = ref(false)
const verifiedFiles = ref([])
const verifiedTotal = ref(0)
const filter = ref('')
const picked = ref([])
const manualGroup = ref(null)
const dupesShown = ref(10)
// Sections a repair changed since they were last checked: their repairs
// stay locked until the section is checked again (the server enforces
// it too, see doctor_routes._require_fresh).
const stale = ref([])
// Duplicate playlists: what to do with each group, chosen while looking
// through them and applied together ({ [group id]: 'merge' | 'apart' }).
const decisions = reactive({})
const playlistKind = ref('all')
const applied = ref(null)
let timer = null

const busy = computed(() => job.value?.state === 'running')
const runningKind = computed(() => (busy.value ? job.value.kind : ''))
const progress = computed(
  () => job.value?.progress || { done: 0, total: 0, step: '' }
)
const stepLabel = computed(() => {
  const step = progress.value.step
  return step ? t(`doctor.step.${step}`) : t('doctor.step.starting')
})
const nd = computed(() => health.value?.navidrome || { enabled: false })

const slskdSummaryText = computed(() => {
  const info = health.value?.slskd
  if (!info) return t('doctor.slskdNotChecked')
  if (info.in_place) return t('doctor.slskdInPlace')
  return t('doctor.slskdFound', {
    files: info.leftovers,
    size: formatBytes(info.bytes),
  })
})
const slskdBadge = computed(() => {
  const info = health.value?.slskd
  if (slskd.value) {
    const count = verifiedCount.value
    return {
      text: count
        ? t('doctor.badge.toDelete', { count })
        : t('doctor.badge.allGood'),
      tone: count ? 'warn' : 'accent',
    }
  }
  if (!info) return { text: t('doctor.badge.notChecked'), tone: 'neutral' }
  if (info.in_place) return { text: t('doctor.badge.allGood'), tone: 'accent' }
  return info.leftovers
    ? {
        text: t('doctor.badge.leftovers', { size: formatBytes(info.bytes) }),
        tone: 'warn',
      }
    : { text: t('doctor.badge.allGood'), tone: 'accent' }
})
const navidromeBadge = computed(() => {
  if (!nd.value.enabled) return { text: t('doctor.badge.off'), tone: 'neutral' }
  if (nd.value.reachable === false) {
    return { text: t('doctor.badge.unreachable'), tone: 'warn' }
  }
  const count =
    (nd.value.duplicates?.length || 0) + (nd.value.orphans?.length || 0)
  return {
    text: countBadge(count, 'toFix'),
    tone: count ? 'warn' : 'accent',
  }
})

// The slskd findings only matter while a check's results are on screen
// to act on; the next check finds everything again anyway.
const slskdStale = computed(() => isStale('slskd') && Boolean(slskd.value))

const playlistGroups = computed(() => health.value?.playlists?.groups || [])
const playlistKindOptions = computed(() => {
  const count = (reason) =>
    playlistGroups.value.filter((g) => g.reason === reason).length
  return [
    {
      value: 'all',
      label: `${t('doctor.kindAll')} (${playlistGroups.value.length})`,
    },
    {
      value: 'name',
      label: `${t('doctor.groupReason.name')} (${count('name')})`,
    },
    {
      value: 'songs',
      label: `${t('doctor.groupReason.songs')} (${count('songs')})`,
    },
  ]
})
const visiblePlaylistGroups = computed(() =>
  playlistKind.value === 'all'
    ? playlistGroups.value
    : playlistGroups.value.filter((g) => g.reason === playlistKind.value)
)
const decidedGroups = (value) =>
  playlistGroups.value.filter((g) => decisions[g.id] === value)
const decidedMerge = computed(() => decidedGroups('merge'))
const decidedApart = computed(() => decidedGroups('apart'))
const decidedCount = computed(
  () => decidedMerge.value.length + decidedApart.value.length
)

function setDecision(id, value) {
  if (value) decisions[id] = value
  else delete decisions[id]
}

function clearDecisions() {
  for (const id of Object.keys(decisions)) delete decisions[id]
}

const memberPaths = (group) => group.members.map((m) => m.path)

async function applyDecisions() {
  const merge = decidedMerge.value
  const apart = decidedApart.value
  const ok = await ui.confirm({
    title: t('doctor.applyTitle'),
    body: t('doctor.applyBody', { merge: merge.length, apart: apart.length }),
    confirmLabel: t('doctor.applyChanges'),
  })
  if (!ok) return
  jobError.value = ''
  try {
    const { data } = await API.doctorPlaylistsApply({
      merge: merge.map(memberPaths),
      apart: apart.map(memberPaths),
    })
    clearDecisions()
    if (data.job) {
      applied.value = null
      applyJob(data.job)
      schedule()
    } else {
      applied.value = { apart: data.apart }
      reloadHealth()
    }
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

async function listPlaylistsAgain() {
  try {
    await API.doctorPlaylistsApartReset()
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
    return
  }
  runHealth()
}

function isStale(section) {
  return stale.value.includes(section)
}

function countBadge(count, key) {
  return count ? t(`doctor.badge.${key}`, { count }) : t('doctor.badge.allGood')
}

function coverOf(path, version) {
  return playlistCoverOf(path, version)
}

const verifiedCount = computed(() => slskd.value?.summary?.verified?.files || 0)
const verifiedBytes = computed(() => slskd.value?.summary?.verified?.bytes || 0)

const filteredM3us = computed(() => {
  const list = health.value?.playlists?.list || []
  const needle = filter.value.toLowerCase()
  return needle
    ? list.filter((item) => item.path.toLowerCase().includes(needle))
    : list
})

// What "Fix" removes in Navidrome: Downtify's API copy of a playlist
// Navidrome also imports (unless the import is missing songs the copy
// has), extra Downtify copies, and imports whose M3U is gone.
const navidromePlan = computed(() => {
  const remove = new Set()
  const blocked = new Set()
  for (const dup of nd.value.duplicates || []) {
    const imports = dup.members.filter((m) => m.kind === 'import')
    const ours = dup.members.filter((m) => m.kind === 'downtify')
    const live = imports.filter((m) => m.m3u_exists)
    for (const stale of imports.filter((m) => !m.m3u_exists)) {
      remove.add(stale.id)
    }
    if (live.length) {
      const best = Math.max(...live.map((m) => m.songs))
      for (const copy of ours) {
        if (copy.songs <= best) remove.add(copy.id)
        else blocked.add(copy.id)
      }
    } else if (ours.length > 1) {
      const keep = ours.reduce((a, b) => (b.songs > a.songs ? b : a))
      for (const copy of ours) if (copy !== keep) remove.add(copy.id)
    }
  }
  for (const orphan of nd.value.orphans || []) remove.add(orphan.id)
  const pairs = (nd.value.duplicates || []).some(
    (d) => d.reason === 'm3u_and_api'
  )
  return {
    delete: [...remove],
    blocked: [...blocked],
    enableImport: pairs && !nd.value.m3u_import,
  }
})

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString(locale.value)
  } catch {
    return iso
  }
}

function dupeText(kind) {
  const totals = health.value?.duplicates?.totals?.[kind] || {}
  return t('doctor.duplicatesCounts', {
    groups: totals.groups || 0,
    files: totals.files || 0,
    size: formatBytes(totals.bytes || 0),
  })
}

function errorOf(err) {
  const detail = err?.response?.data?.detail
  const code = typeof detail === 'object' ? detail?.code : ''
  if (code) return t(`doctor.error.${code}`)
  return typeof detail === 'string' ? detail : t('toast.actionFailed')
}

// The status is polled: each finished job's result is applied once
// (`handled`), and only jobs this page saw running (`watched`) lead to
// a follow-up health check.
let handled = ''
const watched = new Set()

function applyJob(current) {
  job.value = current
  if (!current) return
  if (current.state === 'running') {
    watched.add(current.id)
    return
  }
  if (current.id === handled) return
  const fresh = watched.has(current.id)
  handled = current.id
  if (current.state === 'failed') {
    const code = current.error?.code
    jobError.value = code ? t(`doctor.error.${code}`) : t('toast.actionFailed')
    return
  }
  jobError.value = ''
  const result = current.result
  if (current.kind === 'health') health.value = result
  if (current.kind === 'slskd') {
    slskd.value = result
    cleaned.value = null
    loadVerified(0)
  }
  if (current.kind === 'slskd_clean') {
    cleaned.value = result
    slskd.value = null
    verifiedFiles.value = []
    const info = health.value?.slskd
    if (info) {
      info.leftovers = Math.max(0, info.leftovers - result.deleted)
      info.bytes = Math.max(0, info.bytes - result.bytes)
    }
  }
  if (current.kind === 'formats') {
    formatsFound.value = result
    formatsConverted.value = null
  }
  if (current.kind === 'convert') {
    formatsConverted.value = result
    // What was converted is off the list; the rest can still be.
    const done = new Set(result.converted.map((c) => c.file))
    const found = formatsFound.value
    if (found) {
      const files = found.files.filter((f) => !done.has(f.file))
      formatsFound.value = {
        ...found,
        files,
        count: files.length,
        bytes: files.reduce((sum, f) => sum + f.size, 0),
        estimated: files.reduce((sum, f) => sum + f.estimated, 0),
      }
    }
  }
  if (current.kind === 'merge') merged.value = result
  if (current.kind === 'playlists') applied.value = result
  if (current.kind === 'navidrome') ndResult.value = result
  if (current.kind === 'dedupe') {
    // The server took the merged copies out of its last health check.
    deduped.value = result
    reloadHealth()
  }
  // A repair changes what the health check found: look again, once the
  // repair's own result is on screen.
  if (fresh && ['merge', 'playlists', 'navidrome'].includes(current.kind)) {
    setTimeout(runHealth, 0)
  }
}

async function refresh() {
  try {
    const { data } = await API.doctorStatus()
    holdingQueue.value = data.holding_queue
    stale.value = data.stale || []
    if (!health.value && data.last?.health) {
      health.value = data.last.health.result
    }
    if (!formatsFound.value && data.last?.formats) {
      formatsFound.value = data.last.formats.result
    }
    const wasRunning = busy.value
    applyJob(data.job)
    if (wasRunning && !busy.value && data.job?.kind !== 'health') {
      holdingQueue.value = data.holding_queue
    }
  } catch (err) {
    jobError.value = errorOf(err)
  }
  schedule()
}

function schedule() {
  clearTimeout(timer)
  timer = setTimeout(refresh, busy.value ? 1500 : 10000)
}

async function start(call) {
  jobError.value = ''
  try {
    const { data } = await call()
    applyJob(data)
    schedule()
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

function runHealth() {
  start(() => API.doctorScan())
}

async function runSlskdScan() {
  const ok = await ui.confirm({
    title: t('doctor.slskdCheckTitle'),
    body: t('doctor.slskdCheckBody'),
    confirmLabel: t('doctor.slskdCheck'),
  })
  if (!ok) return
  holdingQueue.value = true
  start(() => API.doctorSlskdScan())
}

function runFormatsScan(formats) {
  start(() => API.doctorFormatsScan(formats))
}

function convertFormats(files) {
  formatsConverted.value = null
  start(() => API.doctorFormatsConvert(files))
}

async function loadVerified(offset) {
  try {
    const { data } = await API.doctorSlskdFiles({
      status: 'verified',
      offset,
      limit: 25,
    })
    verifiedTotal.value = data.total
    verifiedFiles.value = offset
      ? [...verifiedFiles.value, ...data.files]
      : data.files
  } catch {
    verifiedFiles.value = []
  }
}

async function cleanSlskd() {
  const ok = await ui.confirm({
    title: t('doctor.slskdDeleteTitle'),
    body: t('doctor.slskdDeleteBody', {
      files: verifiedCount.value,
      size: formatBytes(verifiedBytes.value),
    }),
    confirmLabel: t('doctor.slskdDeleteConfirm'),
    danger: true,
  })
  if (!ok) return
  holdingQueue.value = false
  start(() => API.doctorSlskdClean())
}

async function releaseSlskd() {
  try {
    await API.doctorSlskdRelease()
    holdingQueue.value = false
    slskd.value = null
    verifiedFiles.value = []
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

async function cancelJob() {
  await API.doctorCancel()
}

async function preview() {
  try {
    manualGroup.value = (await API.doctorPreview(picked.value)).data
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  }
}

async function mergePlaylists(group) {
  const ok = await ui.confirm({
    title: t('doctor.mergeTitle'),
    body: t('doctor.mergeBody', {
      keeper: group.keeper,
      songs: group.songs_after,
    }),
    confirmLabel: t('doctor.merge'),
  })
  if (!ok) return
  start(() => API.doctorMerge(group.members.map((m) => m.path)))
}

async function reloadHealth() {
  try {
    const { data } = await API.doctorStatus()
    stale.value = data.stale || []
    if (data.last?.health) health.value = data.last.health.result
  } catch {
    // The next poll tries again.
  }
}

async function mergeDuplicates({ keep, remove }) {
  const trash = Boolean(health.value?.duplicates?.trash)
  const ok = await ui.confirm({
    title: t('doctor.dupeMergeTitle'),
    body: t('doctor.dupeMergeBody', {
      keep,
      count: remove.length,
      where: trash ? t('doctor.dupeToTrash') : t('doctor.dupeForGood'),
    }),
    confirmLabel: t('doctor.dupeMergeConfirm'),
    danger: !trash,
  })
  if (!ok) return
  deduped.value = null
  start(() => API.doctorDuplicatesMerge(keep, remove))
}

async function keepAllDuplicates(files) {
  try {
    await API.doctorDuplicatesKeep(files)
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
    return
  }
  ui.toast(t('doctor.dupeKeptAllDone'))
  reloadHealth()
}

async function listKeptAgain() {
  try {
    await API.doctorDuplicatesKeepReset()
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
    return
  }
  runHealth()
}

async function repairNavidrome() {
  const plan = navidromePlan.value
  const ok = await ui.confirm({
    title: t('doctor.navidromeFixTitle'),
    body:
      t('doctor.navidromeFixBody', { count: plan.delete.length }) +
      (plan.enableImport ? ' ' + t('doctor.navidromeFixImport') : ''),
    confirmLabel: t('doctor.navidromeFix'),
  })
  if (!ok) return
  start(() =>
    API.doctorNavidromeRepair({
      delete: plan.delete,
      enable_m3u_import: plan.enableImport,
    })
  )
}

onMounted(refresh)
onBeforeUnmount(() => clearTimeout(timer))
</script>
