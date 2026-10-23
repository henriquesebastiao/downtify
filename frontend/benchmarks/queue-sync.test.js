// Opt-in timing experiment, not a wall-clock assertion in CI.
import { execFileSync } from 'node:child_process'
import { performance } from 'node:perf_hooks'
import { env } from 'node:process'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { writeFileSync, unlinkSync } from 'node:fs'
import { describe, expect, it, vi } from 'vitest'

const fixture = vi.hoisted(() => ({ jobs: [] }))
vi.mock('/src/model/api', () => ({
  default: {
    getQueue: async () => ({ data: fixture.jobs }),
    onMessage: () => {},
    downloadFileURL: (file) => `/media/${file}`,
  },
}))
vi.mock('/src/model/settings', () => ({
  useSettingsManager: () => ({ settings: { value: {} } }),
}))

function generatedJobs(count) {
  return Array.from({ length: count }, (_, i) => ({
    song: {
      song_id: `generated:${i}`,
      name: `Track ${i}`,
      artists: ['Generated artist'],
    },
    status: i % 5 === 0 ? 'done' : i % 5 === 1 ? 'downloading' : 'queued',
    progress: i % 5 === 0 ? 100 : i % 5 === 1 ? 20 : 0,
    filename: i % 5 === 0 ? `generated/${i}.mp3` : null,
    provider: 'youtube-music',
    position: i + 1,
    message: '',
  }))
}

function snapshot(model) {
  return model.useProgressTracker().downloadQueue.value.map((item) => ({
    key: item.key,
    state: item.state,
    progress: item.progress,
    provider: item.provider,
    message: item.message,
    position: item.position,
    filename: item.filename,
    url: item.web_download_url,
  }))
}

function median(samples) {
  return [...samples].sort((a, b) => a - b)[Math.floor(samples.length / 2)]
}

async function measure(load, count) {
  vi.resetModules()
  fixture.jobs = []
  const model = await load()
  await model.syncQueueFromServer()
  fixture.jobs = generatedJobs(count)
  const started = performance.now()
  await model.syncQueueFromServer()
  const initial = performance.now() - started
  const tracker = model.useProgressTracker()
  const unchanged = []
  const changed = []
  const versionBefore = tracker.queueVersion.value
  for (let i = 0; i < 3; i++) {
    const start = performance.now()
    await model.syncQueueFromServer()
    unchanged.push(performance.now() - start)
  }
  const unchangedNotifications = tracker.queueVersion.value - versionBefore
  for (let i = 0; i < 3; i++) {
    fixture.jobs = fixture.jobs.map((row, index) =>
      index % 10 === 1 ? { ...row, progress: row.progress + 1 } : row
    )
    const start = performance.now()
    await model.syncQueueFromServer()
    changed.push(performance.now() - start)
  }
  vi.clearAllTimers()
  return {
    final: snapshot(model),
    timing: {
      initial_ms: initial,
      unchanged_median_ms: median(unchanged),
      changed_median_ms: median(changed),
      unchanged_notifications: unchangedNotifications,
    },
  }
}

describe.skipIf(env.DOWNTIFY_QUEUE_BENCHMARK !== '1')(
  'real queue synchronization benchmark',
  () => {
    it('compares generated snapshots with the public baseline', async () => {
      vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
      const here = dirname(fileURLToPath(import.meta.url))
      const ref =
        env.DOWNTIFY_QUEUE_BASELINE_REF ||
        '6d7bebf00d7e41c011645b9ebe1de004c9e31e74'
      const baseline = execFileSync(
        'git',
        ['show', `${ref}:frontend/src/model/download.js`],
        {
          cwd: resolve(here, '../..'),
          encoding: 'utf8',
        }
      )
      const temporary = join(here, `.queue-baseline-${process.pid}.js`)
      writeFileSync(temporary, baseline)
      try {
        const results = []
        for (const count of [250, 2000, 10000]) {
          const old = await measure(
            () => import(/* @vite-ignore */ pathToFileURL(temporary).href),
            count
          )
          const current = await measure(
            () => import('../src/model/download.js'),
            count
          )
          expect(current.final).toEqual(old.final)
          expect(current.timing.unchanged_notifications).toBe(0)
          results.push({
            rows: count,
            baseline: old.timing,
            current: current.timing,
          })
        }
        const report = JSON.stringify({ ref, results }, null, 2)
        if (env.DOWNTIFY_QUEUE_BENCHMARK_OUTPUT) {
          writeFileSync(env.DOWNTIFY_QUEUE_BENCHMARK_OUTPUT, report + '\n')
        }
        console.log('QUEUE_SYNC_BENCHMARK ' + report)
      } finally {
        unlinkSync(temporary)
        vi.clearAllTimers()
        vi.useRealTimers()
      }
    }, 240000)
  }
)
