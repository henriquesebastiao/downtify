// Settings > Notifications helpers (downtify/notification_routes.py).
// The server never sends a secret back: each one arrives as `<key>_set`.
// The form holds what the admin typed instead (blank: keep the saved
// one), and `clear` lists the saved secrets to remove.

export const SECRETS = {
  discord: ['webhook_url', 'bot_token'],
  ntfy: ['token'],
  gotify: ['token'],
  webhook: ['url'],
}

/** A form copy of the server's settings, every secret blank. */
export function formFrom(settings) {
  const form = JSON.parse(JSON.stringify(settings || {}))
  for (const [name, keys] of Object.entries(SECRETS)) {
    const ch = form.channels?.[name]
    if (!ch) continue
    for (const key of keys) {
      delete ch[`${key}_set`]
      ch[key] = ''
    }
  }
  return form
}

/** Whether `secret` of `channel` is saved and not about to be cleared. */
export function secretSaved(settings, clear, channel, secret) {
  return (
    !!settings?.channels?.[channel]?.[`${secret}_set`] &&
    !clear.includes(`${channel}.${secret}`)
  )
}

/** The body of `PUT /api/notifications`. */
export function savePayload(form, clear) {
  return { settings: form, clear: [...clear] }
}

/** Add or remove `value` from the list `list` (a channel's tasks...). */
export function toggled(list, value) {
  return list.includes(value)
    ? list.filter((item) => item !== value)
    : [...list, value]
}

/** Whether a channel has what it needs to send (as the server checks),
 *  counting saved secrets. */
export function channelReady(name, ch, saved) {
  const has = (key) => !!ch?.[key] || !!saved?.[`${key}_set`]
  if (name === 'discord') {
    if (ch?.mode === 'bot') return has('bot_token') && !!ch.channel_id
    return has('webhook_url')
  }
  if (name === 'ntfy') return !!ch?.topic
  if (name === 'gotify') return !!ch?.server && has('token')
  return has('url')
}
