export function playlistChoices(playlists, recent = []) {
  const byName = new Map(playlists.map((item) => [item.name, item]))
  const ordered = [...new Set([...recent, ...byName.keys()])]
    .map((name) => byName.get(name))
    .filter(Boolean)
  return { quick: ordered.slice(0, 3), others: ordered.slice(3) }
}

export function rememberPlaylist(recent, name) {
  return [name, ...recent.filter((item) => item !== name)].slice(0, 100)
}
