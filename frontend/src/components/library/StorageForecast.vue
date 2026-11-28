<template>
  <UiPanel
    v-if="summary"
    :title="t('usage.forecast.title')"
    :description="t('usage.forecast.hint', { weeks: windowWeeks })"
  >
    <div class="flex flex-col gap-5">
      <!-- The headline -->
      <div v-if="summary.state">
        <p
          class="text-2xl font-semibold text-pretty"
          :class="TONE_TEXT[summary.tone] || ''"
        >
          {{ headline }}
        </p>
        <p v-if="subline" class="mt-1 text-[13px] text-pretty text-muted">
          {{ subline }}
        </p>
        <p
          v-if="summary.rough"
          class="mt-2 flex items-start gap-2 text-[13px] text-muted"
        >
          <AppIcon name="info" :size="15" class="mt-0.5 shrink-0" />
          {{ t('usage.forecast.rough', { count: summary.historyDays }) }}
        </p>
      </div>

      <!-- The two paces -->
      <dl class="grid grid-cols-2 gap-3">
        <div class="rounded-panel border border-line-2 px-3 py-2">
          <dt class="text-[12px] text-muted">
            {{ t('usage.forecast.usualPace') }}
          </dt>
          <dd class="tabular mt-0.5 font-semibold">
            {{ perWeek(summary.usualPerWeek) }}
          </dd>
        </div>
        <div class="rounded-panel border border-line-2 px-3 py-2">
          <dt class="text-[12px] text-muted">
            {{ t('usage.forecast.recentPace', { count: summary.recentDays }) }}
          </dt>
          <dd class="tabular mt-0.5 font-semibold">
            {{ perWeek(summary.recentPerWeek) }}
          </dd>
        </div>
      </dl>

      <!-- Still to come: taken off the free space first -->
      <section v-if="summary.stillToCome.songs">
        <h3 class="text-sm font-semibold">
          {{ t('usage.forecast.stillTitle') }}
        </h3>
        <p class="mt-1 text-[13px] text-pretty text-muted">
          {{
            t('usage.forecast.stillHint', {
              songs: summary.stillToCome.songs,
              size: formatBytes(summary.stillToCome.bytes),
              each: formatBytes(summary.stillToCome.average_bytes),
            })
          }}
        </p>
        <ul class="mt-2 flex flex-col gap-1 text-sm">
          <li
            v-if="summary.stillToCome.queued"
            class="flex justify-between gap-3"
          >
            <span class="truncate">{{ t('usage.forecast.queue') }}</span>
            <span class="tabular shrink-0 text-muted">{{
              t('usage.songs', { count: summary.stillToCome.queued })
            }}</span>
          </li>
          <li
            v-for="row in summary.stillToCome.watches || []"
            :key="row.id"
            class="flex justify-between gap-3"
          >
            <span class="truncate">{{ row.name }}</span>
            <span class="tabular shrink-0 text-muted">{{
              t('usage.songs', { count: row.songs })
            }}</span>
          </li>
        </ul>
      </section>

      <!-- Left out of the pace -->
      <section v-if="summary.oneOff.bytes || summary.spikes.length">
        <h3 class="text-sm font-semibold">
          {{ t('usage.forecast.leftOutTitle') }}
        </h3>
        <p class="mt-1 text-[13px] text-pretty text-muted">
          {{ t('usage.forecast.leftOutHint') }}
        </p>
        <ul class="mt-2 flex flex-col gap-1 text-sm">
          <li
            v-for="row in summary.oneOff.watches"
            :key="`w${row.id}`"
            class="flex justify-between gap-3"
          >
            <span class="truncate">
              {{ t('usage.forecast.firstCheck', { name: row.name }) }}
            </span>
            <span class="tabular shrink-0 text-muted">
              +{{ formatBytes(row.bytes) }}
            </span>
          </li>
          <li
            v-for="spike in summary.spikes"
            :key="spike.from"
            class="flex justify-between gap-3"
          >
            <span class="truncate">
              {{
                t('usage.forecast.busyWeek', {
                  from: formatDay(spike.from, locale),
                  to: formatDay(spike.to, locale),
                })
              }}
            </span>
            <span class="tabular shrink-0 text-muted">
              +{{ formatBytes(spike.bytes) }}
            </span>
          </li>
        </ul>
      </section>

      <!-- What makes it grow -->
      <section v-if="drivers.length">
        <h3 class="text-sm font-semibold">
          {{ t('usage.forecast.driversTitle') }}
        </h3>
        <p class="mt-1 text-[13px] text-pretty text-muted">
          {{ t('usage.forecast.driversHint', { weeks: windowWeeks }) }}
        </p>
        <ul class="mt-2 flex flex-col gap-1 text-sm">
          <li
            v-for="row in drivers"
            :key="row.key"
            class="flex justify-between gap-3"
          >
            <span class="truncate" :class="row.muted ? 'text-muted' : ''">
              {{ row.name }}
            </span>
            <span class="tabular shrink-0 text-muted">
              {{ perWeek(row.perWeek, true) }}
            </span>
          </li>
        </ul>
      </section>
    </div>
  </UiPanel>
</template>

<script setup>
// "When is the disk full?" on the Storage and usage page: the forecast
// part of GET /api/library/usage (downtify/storage_forecast.py). The
// server works everything out; this only words it.
import { computed } from 'vue'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import { formatBytes } from '/src/lib/format'
import { forecastSummary, formatDay, timeSpan } from '/src/lib/libraryUsage'
import { useI18n } from '/src/i18n'

const TONE_TEXT = { danger: 'text-danger', warn: 'text-warn' }

const props = defineProps({
  forecast: { type: Object, default: null },
  disk: { type: Object, default: null },
})

const { t, locale } = useI18n()

const summary = computed(() => forecastSummary(props.forecast))
const windowWeeks = computed(() =>
  Math.round((props.forecast?.window_days || 84) / 7)
)

function spanText(span) {
  return t(`usage.forecast.span.${span.unit}`, { count: span.count })
}

function perWeek(bytes, signed = false) {
  const value = Number(bytes) || 0
  const sign = signed && value > 0 ? '+' : value < 0 ? '−' : ''
  return t('usage.perWeekRate', {
    size: `${sign}${formatBytes(Math.abs(value))}`,
  })
}

const headline = computed(() => {
  const s = summary.value
  if (!s) return ''
  if (s.state === 'ok')
    return t('usage.forecast.fullIn', { span: spanText(s.span) })
  if (s.state === 'beyond') return t('usage.forecast.beyond')
  if (s.state === 'not_growing') return t('usage.forecast.notGrowing')
  if (s.state === 'backlog_too_big') return t('usage.forecast.backlogTooBig')
  return ''
})

const subline = computed(() => {
  const s = summary.value
  if (!s) return ''
  if (s.state === 'ok') {
    const around = t('usage.forecast.around', {
      date: longDate(s.full.date),
      free: formatBytes(props.disk?.free),
    })
    if (!s.range) return around
    return `${around} ${t('usage.forecast.range', {
      soonest: whenText(s.range.soonest),
      latest: whenText(s.range.latest),
    })}`
  }
  if (s.state === 'backlog_too_big') {
    return t('usage.forecast.backlogTooBigHint', {
      size: formatBytes(s.stillToCome.bytes),
      free: formatBytes(props.disk?.free),
    })
  }
  if (s.state === 'not_growing') return t('usage.forecast.notGrowingHint')
  return ''
})

function whenText(when) {
  return when.beyond
    ? t('usage.forecast.tenYears')
    : spanText(timeSpan(when.days))
}

function longDate(day) {
  const date = new Date(`${day}T00:00:00Z`)
  if (Number.isNaN(date.getTime())) return String(day || '')
  try {
    return date.toLocaleDateString(locale.value, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: 'UTC',
    })
  } catch {
    return day
  }
}

const drivers = computed(() => {
  const d = summary.value?.drivers
  if (!d) return []
  const rows = (d.watches || []).map((row) => ({
    key: `w${row.id}`,
    name: row.name,
    perWeek: row.per_week_bytes,
  }))
  if (d.more_watches) {
    rows.push({
      key: 'more',
      name: t('usage.forecast.moreWatches', { count: d.more_watches }),
      perWeek: Math.round(
        ((d.more_watches_bytes || 0) / (props.forecast?.history_days || 1)) * 7
      ),
      muted: true,
    })
  }
  if (rows.length || d.other_per_week_bytes) {
    rows.push({
      key: 'other',
      name: t('usage.forecast.otherGrowth'),
      perWeek: d.other_per_week_bytes,
      muted: true,
    })
  }
  return rows
})
</script>
