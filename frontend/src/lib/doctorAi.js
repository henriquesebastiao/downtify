/**
 * Connection setups for the Doctor's AI helper (Settings > Doctor > AI
 * helper): what to paste into each assistant app, with the helper's
 * address and key filled in.
 */

/** The helper's address: this page's server plus its MCP path. */
export function helperUrl(origin, mcpPath) {
  return `${String(origin || '').replace(/\/+$/, '')}${mcpPath || ''}`
}

/**
 * The setup for *client* (``code``, ``desktop`` or ``other``).
 *
 * Claude Desktop starts the ``mcp-remote`` bridge itself. On Windows it
 * passes arguments with spaces badly, so the header's value comes from an
 * environment variable (the bridge's own advice), and a plain-http address
 * needs ``--allow-http``: the bridge only allows https or localhost by
 * default.
 */
export function connectionSnippet(client, url, key) {
  if (client === 'code') {
    return (
      `claude mcp add --transport http downtify-doctor ${url} ` +
      `--header "Authorization: Bearer ${key}"`
    )
  }
  if (client === 'desktop') {
    const args = ['-y', 'mcp-remote', url, '--header', 'Authorization:${AUTH}']
    if (needsAllowHttp(url)) args.push('--allow-http')
    return JSON.stringify(
      {
        mcpServers: {
          'downtify-doctor': {
            command: 'npx',
            args,
            env: { AUTH: `Bearer ${key}` },
          },
        },
      },
      null,
      2
    )
  }
  return `URL: ${url}\nHeader: Authorization: Bearer ${key}`
}

function needsAllowHttp(url) {
  try {
    const { protocol, hostname } = new URL(url)
    if (protocol !== 'http:') return false
    return !['localhost', '127.0.0.1', '[::1]'].includes(hostname)
  } catch {
    return false
  }
}
