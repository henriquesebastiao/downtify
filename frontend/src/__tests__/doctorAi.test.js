import { describe, expect, it } from 'vitest'

import { connectionSnippet, helperUrl } from '/src/lib/doctorAi'

const KEY = 'dtai_example'

describe('Doctor AI helper connection setups', () => {
  it('builds the address from the page origin', () => {
    expect(helperUrl('http://zima.local:8000/', '/api/doctor/ai/mcp')).toBe(
      'http://zima.local:8000/api/doctor/ai/mcp'
    )
  })

  it('gives Claude Code one command with the key as a header', () => {
    const url = 'http://zima.local:8000/api/doctor/ai/mcp'
    expect(connectionSnippet('code', url, KEY)).toBe(
      `claude mcp add --transport http downtify-doctor ${url} ` +
        `--header "Authorization: Bearer ${KEY}"`
    )
  })

  it('gives Claude Desktop an mcp-remote bridge with the key in env', () => {
    const url = 'http://192.168.1.20:8000/api/doctor/ai/mcp'
    const config = JSON.parse(connectionSnippet('desktop', url, KEY))
    const server = config.mcpServers['downtify-doctor']
    expect(server.command).toBe('npx')
    expect(server.args).toEqual([
      '-y',
      'mcp-remote',
      url,
      '--header',
      'Authorization:${AUTH}',
      '--allow-http',
    ])
    expect(server.env).toEqual({ AUTH: `Bearer ${KEY}` })
  })

  it('asks for --allow-http only for plain http away from this computer', () => {
    const args = (url) =>
      JSON.parse(connectionSnippet('desktop', url, KEY)).mcpServers[
        'downtify-doctor'
      ].args
    expect(args('https://music.example.com/api/doctor/ai/mcp')).not.toContain(
      '--allow-http'
    )
    expect(args('http://localhost:8000/api/doctor/ai/mcp')).not.toContain(
      '--allow-http'
    )
  })

  it('spells the address and header out for other apps', () => {
    expect(connectionSnippet('other', 'https://x/mcp', KEY)).toBe(
      `URL: https://x/mcp\nHeader: Authorization: Bearer ${KEY}`
    )
  })
})
