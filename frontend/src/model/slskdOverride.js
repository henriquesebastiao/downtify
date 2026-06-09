/** Join folder + filename lines copied from the slskd UI. */
export function joinSlskdRemotePath(folder, file) {
  const dir = String(folder || '').trim()
  const name = String(file || '').trim()
  if (!dir || !name) return ''
  if (dir.endsWith('\\') || dir.endsWith('/')) {
    return `${dir}${name}`
  }
  return `${dir}\\${name}`
}

/** Parse manual slskd override pasted from the slskd UI. */
export function parseSlskdOverride(text) {
  const raw = String(text || '').trim()
  if (!raw) return null
  const pipe = raw.indexOf('|')
  if (pipe >= 0) {
    const username = raw.slice(0, pipe).trim()
    const filename = raw.slice(pipe + 1).trim()
    if (username && filename) {
      return { username, filename }
    }
  }
  const match = raw.match(/^(\S+)\s+(@@.+)$/s)
  if (match) {
    return { username: match[1].trim(), filename: match[2].trim() }
  }
  return null
}
