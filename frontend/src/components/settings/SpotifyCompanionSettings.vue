<template>
  <SettingGroup
    :title="t('companion.title')"
    :description="t('companion.hint')"
  >
    <SettingRow
      :label="t('companion.enable')"
      :description="t('companion.enableHint')"
    >
      <UiSwitch
        :model-value="!!form.enabled"
        :aria-label="t('companion.enable')"
        :disabled="!loaded || saving"
        @update:model-value="setEnabled"
      />
    </SettingRow>

    <SettingRow :label="t('companion.status')" stacked>
      <div v-if="view" class="flex w-full flex-col gap-1.5 text-sm">
        <div class="flex flex-wrap items-center gap-2">
          <UiBadge :tone="statusTone(health.status)">{{
            t(`companion.status_${health.status}`)
          }}</UiBadge>
          <span v-if="health.account" class="text-muted">
            {{ t('companion.signedInAs', { name: health.account.name }) }}
          </span>
          <span v-if="health.seen_at" class="text-faint">
            · {{ t('companion.lastSeen', { when: ago(health.seen_at) }) }}
          </span>
        </div>
        <p
          v-if="health.message && health.status !== 'ready'"
          class="text-faint"
        >
          {{ health.message }}
        </p>
        <p class="text-muted">
          {{
            t('companion.counts', {
              mixes: view.mixes,
              due: view.due,
              reads: view.reads_today,
            })
          }}
        </p>
        <p v-if="view.reading" class="text-muted">
          {{ t('companion.readingNow', { name: view.reading.name }) }}
        </p>
        <p v-else-if="nextOpening" class="text-faint">
          {{
            t('companion.nextSlot', {
              name: nextOpening.name,
              time: nextOpening.time,
            })
          }}
        </p>
        <div
          v-if="health.status === 'other_account'"
          class="mt-1 flex flex-col gap-2 rounded-lg border border-warn/40 p-3"
        >
          <p class="text-pretty text-warn">
            {{
              t('companion.otherAccount', {
                name: health.account?.name || '?',
                expected: health.expected_account?.name || '?',
              })
            }}
          </p>
          <div>
            <UiButton :loading="switching" @click="useAccount">
              {{
                t('companion.useAccount', { name: health.account?.name || '?' })
              }}
            </UiButton>
          </div>
        </div>
      </div>
      <UiSkeleton v-else class="h-4 w-56" />
    </SettingRow>

    <SettingRow
      :label="t('companion.slots')"
      :description="t('companion.slotsHint')"
      stacked
    >
      <div class="flex w-full flex-col gap-3">
        <div
          v-for="(slot, index) in form.slots"
          :key="slot.id"
          class="flex flex-col gap-3 rounded-lg border border-line-3 p-3"
        >
          <div class="flex flex-wrap items-end gap-2">
            <UiInput
              v-model="slot.name"
              class="min-w-[10rem] flex-1"
              :label="t('companion.slotName')"
              :placeholder="
                t('companion.slotNamePlaceholder', { n: index + 1 })
              "
            />
            <UiInput
              v-model="slot.start"
              type="time"
              class="w-32"
              :label="t('companion.start')"
            />
            <UiInput
              v-model="slot.end"
              type="time"
              class="w-32"
              :label="t('companion.end')"
            />
            <UiInput
              v-model.number="slot.seats"
              type="number"
              class="w-24"
              min="1"
              max="500"
              :label="t('companion.seats')"
            />
            <UiButton
              icon="trash"
              :aria-label="t('companion.removeSlot')"
              @click="form.slots.splice(index, 1)"
            />
          </div>
          <div
            class="flex flex-wrap gap-1.5"
            role="group"
            :aria-label="t('companion.days')"
          >
            <button
              v-for="day in DAYS"
              :key="day"
              type="button"
              class="rounded-full border px-2.5 py-1 text-xs font-semibold"
              :class="
                slot.days.includes(day)
                  ? 'border-transparent bg-accent/15 text-accent'
                  : 'border-line-3 text-muted'
              "
              :aria-pressed="slot.days.includes(day)"
              @click="slot.days = toggled(slot.days, day, DAYS)"
            >
              {{ days[day] }}
            </button>
          </div>
          <div class="flex flex-wrap gap-x-4 gap-y-1.5 text-sm">
            <label
              v-for="kind in KINDS"
              :key="kind"
              class="inline-flex items-center gap-2"
            >
              <input
                type="checkbox"
                class="accent-[var(--color-accent)]"
                :checked="slot.kinds.includes(kind)"
                @change="slot.kinds = toggled(slot.kinds, kind, KINDS)"
              />
              {{ t(`companion.kind_${kind}`) }}
            </label>
          </div>
          <p v-if="usage(slot)" class="text-xs text-faint">{{ usage(slot) }}</p>
          <p v-if="slotProblem(slot)" class="text-xs text-danger">
            {{ t(slotProblem(slot)) }}
          </p>
        </div>
        <div>
          <UiButton icon="plus" @click="form.slots.push(newSlot(form.slots))">
            {{ t('companion.addSlot') }}
          </UiButton>
        </div>
      </div>
    </SettingRow>

    <SettingRow
      :label="t('companion.minGap')"
      :description="t('companion.minGapHint')"
    >
      <UiInput
        v-model.number="form.min_gap_seconds"
        type="number"
        min="20"
        max="3600"
        class="w-28"
        :aria-label="t('companion.minGap')"
      />
    </SettingRow>
    <SettingRow
      :label="t('companion.awayAlert')"
      :description="t('companion.awayAlertHint')"
    >
      <UiInput
        v-model.number="form.away_alert_hours"
        type="number"
        min="1"
        max="72"
        class="w-28"
        :aria-label="t('companion.awayAlert')"
      />
    </SettingRow>
    <SettingRow :label="''" stacked>
      <div class="flex items-center gap-3">
        <UiButton
          variant="primary"
          :loading="saving"
          :disabled="!loaded || hasProblem"
          @click="save()"
        >
          {{ t('companion.save') }}
        </UiButton>
        <span class="text-sm text-faint" role="status">{{ savedNote }}</span>
      </div>
    </SettingRow>

    <SettingRow
      :label="t('companion.download')"
      :description="t('companion.downloadHint')"
      stacked
    >
      <div class="flex flex-wrap gap-2">
        <UiButton icon="download" :loading="downloading" @click="download">
          {{ t('companion.download') }}
        </UiButton>
        <UiButton :href="GUIDE_URL" icon="link" icon-right="arrow-up-right">
          {{ t('companion.guide') }}
        </UiButton>
      </div>
    </SettingRow>

    <SettingRow
      :label="t('companion.agent')"
      :description="t('companion.agentHint')"
      stacked
    >
      <div class="flex w-full flex-col gap-3">
        <div class="flex w-full flex-col gap-2 sm:flex-row sm:items-end">
          <UiInput
            v-model="agentAddress"
            class="min-w-0 flex-1"
            :label="t('companion.agentAddress')"
            :hint="t('companion.agentAddressHint')"
            placeholder="http://192.168.1.20:8000"
          />
          <UiButton icon="sparkle" :loading="agentBusy" @click="makeAgentSetup">
            {{ t('companion.agentMake') }}
          </UiButton>
        </div>
        <template v-if="agentText">
          <p class="text-[13px] text-pretty text-warn" role="status">
            {{ t('companion.agentReady', { time: agentUntil }) }}
          </p>
          <textarea
            :value="agentText"
            readonly
            rows="10"
            class="w-full rounded-lg border border-line-3 bg-bg p-3 font-mono text-[12px] text-fg"
            :aria-label="t('companion.agent')"
          ></textarea>
          <div>
            <UiButton icon="copy" @click="copyAgent">
              {{
                agentCopied
                  ? t('companion.agentCopied')
                  : t('companion.agentCopy')
              }}
            </UiButton>
          </div>
        </template>
      </div>
    </SettingRow>
  </SettingGroup>
</template>

<script setup>
// Settings > Apps > Spotify companion: the browser extension that reads
// your own version of Spotify's personal mixes
// (downtify/spotify_companion.py). Its settings save themselves (they
// aren't part of settings.json), so this card has its own Save button.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import API from '/src/model/api'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'
import { timeAgo } from '/src/lib/format'
import {
  DAYS,
  KINDS,
  dayNames,
  newSlot,
  slotProblem,
  statusTone,
  toggled,
} from '/src/lib/spotifyCompanion'

const emit = defineEmits(['key-made'])
const { t, locale } = useI18n()
const ui = useUi()
const GUIDE_URL =
  'https://henriquesebastiao.github.io/downtify/features/spotify-companion'

const view = ref(null)
const form = ref({
  enabled: false,
  slots: [],
  min_gap_seconds: 45,
  away_alert_hours: 6,
})
const loaded = ref(false)
const saving = ref(false)
const switching = ref(false)
const downloading = ref(false)
const savedNote = ref('')
let timer = null

// "Set up with an AI agent" (downtify/spotify_companion_agent.py).
const agentAddress = ref('')
const agentText = ref('')
const agentUntil = ref('')
const agentBusy = ref(false)
const agentCopied = ref(false)

async function makeAgentSetup() {
  agentBusy.value = true
  agentCopied.value = false
  try {
    const res = await API.companionAgent(agentAddress.value.trim())
    agentText.value = res.data.instructions
    agentUntil.value = new Date(res.data.expires_at).toLocaleString(
      locale.value
    )
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    agentBusy.value = false
  }
}

async function copyAgent() {
  try {
    await navigator.clipboard.writeText(agentText.value)
    agentCopied.value = true
  } catch {
    // The text stays selectable in the box.
  }
}

const days = computed(() => dayNames(locale.value))
const health = computed(() => view.value?.health || { status: 'off' })
const hasProblem = computed(() => form.value.slots.some((s) => slotProblem(s)))

const nextOpening = computed(() => {
  const next = view.value?.next_opening
  if (!next) return null
  const slot = form.value.slots.find((s) => s.id === next.id)
  return {
    name: slot?.name || next.id,
    time: new Date(next.at).toLocaleString(locale.value, {
      weekday: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }),
  }
})

function ago(iso) {
  return timeAgo(iso, locale.value)
}

function usage(slot) {
  const found = view.value?.slots?.find((s) => s.id === slot.id)
  if (!found?.open) return ''
  return t('companion.seatsUsed', { used: found.used, seats: slot.seats })
}

function apply(data) {
  const { config, ...rest } = data
  view.value = rest
  form.value = JSON.parse(JSON.stringify(config))
}

async function load({ keepForm = false } = {}) {
  try {
    const res = await API.companionStatus()
    if (keepForm) {
      const { config: _config, ...rest } = res.data
      view.value = rest
    } else {
      apply(res.data)
    }
    loaded.value = true
  } catch {
    // Shown as loading; the next refresh tries again.
  }
}

async function save(patch = null) {
  saving.value = true
  savedNote.value = ''
  try {
    const res = await API.companionSave(patch || form.value)
    apply(res.data)
    savedNote.value = t('companion.saved')
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    saving.value = false
  }
}

function setEnabled(value) {
  form.value.enabled = value
  save({ enabled: value })
}

async function useAccount() {
  switching.value = true
  try {
    apply((await API.companionUseAccount()).data)
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  } finally {
    switching.value = false
  }
}

async function download() {
  downloading.value = true
  try {
    const res = await API.companionExtension()
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'downtify-companion.zip'
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 10000)
    emit('key-made')
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  } finally {
    downloading.value = false
  }
}

onMounted(() => {
  load()
  timer = setInterval(() => load({ keepForm: true }), 30000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>
