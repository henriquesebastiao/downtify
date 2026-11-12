import { describe, expect, it } from 'vitest'
import {
  MONITOR_COLUMNS,
  monitorLayout,
  resizeMonitorColumn,
  toggleMonitorColumn,
} from '../lib/monitorColumns'

describe('monitor column preferences', () => {
  it('reserves room for artist identity and actions by default', () => {
    const layout = monitorLayout(null)
    expect(layout.widths.name).toBeGreaterThanOrEqual(240)
    expect(layout.widths.actions).toBeGreaterThanOrEqual(128)
    expect(layout.hidden).toEqual([])
  })
  it('rejects CSS strings and nonfinite persisted widths', () => {
    const layout = monitorLayout({
      widths: { name: '0px;display:none', source: NaN, checks: Infinity },
    })
    expect(layout.widths.name).toBe(320)
    expect(layout.widths.source).toBe(140)
    expect(layout.widths.checks).toBe(190)
  })
  it('bounds and rounds every persisted dimension', () => {
    for (const col of MONITOR_COLUMNS) {
      expect(resizeMonitorColumn({}, col.key, -100).widths[col.key]).toBe(
        col.min
      )
      expect(resizeMonitorColumn({}, col.key, 10000).widths[col.key]).toBe(
        col.max
      )
      expect(
        resizeMonitorColumn({}, col.key, col.min + 0.7).widths[col.key]
      ).toBe(col.min + 1)
    }
  })
  it('cannot hide required columns or introduce unknown columns', () => {
    expect(
      monitorLayout({
        hidden: ['name', 'actions', 'unknown', 'source', 'source'],
      }).hidden
    ).toEqual(['source'])
    expect(toggleMonitorColumn({}, 'name').hidden).toEqual([])
    expect(
      Object.hasOwn(resizeMonitorColumn({}, 'unknown', 12).widths, 'unknown')
    ).toBe(false)
  })
  it('toggles optional columns without mutating its input', () => {
    const original = monitorLayout({})
    const hidden = toggleMonitorColumn(original, 'source')
    expect(hidden.hidden).toEqual(['source'])
    expect(original.hidden).toEqual([])
    expect(toggleMonitorColumn(hidden, 'source').hidden).toEqual([])
  })
  it('round trips preferences and keeps defaults recoverable', () => {
    const value = toggleMonitorColumn(
      resizeMonitorColumn({}, 'name', 550),
      'checked'
    )
    expect(monitorLayout(JSON.parse(JSON.stringify(value)))).toEqual(value)
    expect(monitorLayout({}).widths.name).toBe(320)
  })
})
