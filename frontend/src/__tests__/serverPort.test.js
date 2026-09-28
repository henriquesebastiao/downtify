import { describe, expect, it } from 'vitest'
import {
  pagePort,
  portField,
  reachesDirectly,
  urlOnPort,
  validPort,
} from '../lib/serverPort.js'

const at = (href) => {
  const url = new URL(href)
  return { href, port: url.port, protocol: url.protocol }
}

describe('server port helpers', () => {
  it('knows the port a page came from', () => {
    expect(pagePort(at('http://nas:8000/settings'))).toBe(8000)
    expect(pagePort(at('https://music.example/'))).toBe(443)
    expect(pagePort(at('http://nas/'))).toBe(80)
  })

  it('follows a port change only when talking to the server directly', () => {
    expect(reachesDirectly(at('http://nas:8000/'), 8000)).toBe(true)
    expect(reachesDirectly(at('https://music.example/'), 8000)).toBe(false)
  })

  it('builds the new address', () => {
    expect(urlOnPort(at('http://nas:8000/settings/apps?x=1'), 9000)).toBe(
      'http://nas:9000/settings/apps?x=1'
    )
  })

  it('shows the port in use, read-only, when the environment sets it', () => {
    expect(
      portField({ port: 30321, next: 30321, locked_by: 'DOWNTIFY_PORT' })
    ).toEqual({ value: '30321', editable: false })
    // The environment changed since the start: still the port in use.
    expect(
      portField({ port: 8000, next: 30321, locked_by: 'DOWNTIFY_PORT' })
    ).toEqual({ value: '8000', editable: false })
    expect(portField({ port: 8000, next: 9000, locked_by: '' })).toEqual({
      value: '9000',
      editable: true,
    })
    expect(portField(null).editable).toBe(false)
  })

  it('accepts only ports in range', () => {
    expect(validPort('8080')).toBe(true)
    expect(validPort(' 9000 ')).toBe(true)
    expect(validPort('80')).toBe(false)
    expect(validPort('70000')).toBe(false)
    expect(validPort('80a')).toBe(false)
    expect(validPort('')).toBe(false)
  })
})
