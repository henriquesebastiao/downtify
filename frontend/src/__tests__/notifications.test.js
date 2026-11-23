import { describe, expect, it } from 'vitest'
import {
  channelReady,
  formFrom,
  savePayload,
  secretSaved,
  toggled,
} from '../lib/notifications'

const server = {
  enabled: true,
  progress_seconds: 60,
  channels: {
    discord: {
      enabled: true,
      mode: 'webhook',
      webhook_url_set: true,
      bot_token_set: false,
      channel_id: '',
    },
    ntfy: { enabled: false, topic: '', token_set: false },
    gotify: { enabled: false, server: '', token_set: true },
    webhook: { enabled: false, url_set: false },
  },
}

describe('notification settings form', () => {
  it('starts every secret blank and drops the _set flags', () => {
    const form = formFrom(server)
    expect(form.channels.discord.webhook_url).toBe('')
    expect(form.channels.discord).not.toHaveProperty('webhook_url_set')
    expect(form.channels.gotify.token).toBe('')
    // The server's copy is left alone.
    expect(server.channels.discord.webhook_url_set).toBe(true)
  })

  it('knows which secrets are saved, unless about to be cleared', () => {
    expect(secretSaved(server, [], 'discord', 'webhook_url')).toBe(true)
    expect(
      secretSaved(server, ['discord.webhook_url'], 'discord', 'webhook_url')
    ).toBe(false)
    expect(secretSaved(server, [], 'discord', 'bot_token')).toBe(false)
  })

  it('sends the form and the secrets to clear', () => {
    const form = formFrom(server)
    expect(savePayload(form, ['gotify.token'])).toEqual({
      settings: form,
      clear: ['gotify.token'],
    })
  })

  it('toggles a choice in a list', () => {
    expect(toggled(['a', 'b'], 'a')).toEqual(['b'])
    expect(toggled(['b'], 'a')).toEqual(['b', 'a'])
  })

  it('says when a channel can send', () => {
    const saved = server.channels.discord
    expect(channelReady('discord', { mode: 'webhook' }, saved)).toBe(true)
    expect(
      channelReady('discord', { mode: 'bot', channel_id: '1' }, saved)
    ).toBe(false)
    expect(
      channelReady(
        'discord',
        { mode: 'bot', channel_id: '1', bot_token: 'x' },
        saved
      )
    ).toBe(true)
    expect(channelReady('ntfy', { topic: 'x' }, {})).toBe(true)
    expect(channelReady('gotify', { server: 'https://g' }, {})).toBe(false)
    expect(channelReady('webhook', { url: 'https://w' }, {})).toBe(true)
  })
})
