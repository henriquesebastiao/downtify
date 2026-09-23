// Downtify's icon set: 24px grid, drawn as strokes (1.8) unless listed in
// FILLED. Bundled with the app instead of fetched from an icon CDN, so
// the UI renders the same on an offline home server.

export const STROKE = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  library: '<path d="M4 4v16M9 4v16M14 4l6 16"/>',
  download: '<path d="M12 3v12m0 0-4.5-4.5M12 15l4.5-4.5M4 20h16"/>',
  upload: '<path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M4 20h16"/>',
  radar:
    '<path d="M4.9 19.1a10 10 0 0 1 0-14.2M19.1 4.9a10 10 0 0 1 0 14.2M7.8 16.2a6 6 0 0 1 0-8.4M16.2 7.8a6 6 0 0 1 0 8.4"/><circle cx="12" cy="12" r="2"/>',
  settings:
    '<path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  'chevron-down': '<path d="m6 9 6 6 6-6"/>',
  'chevron-up': '<path d="m6 15 6-6 6 6"/>',
  'chevron-right': '<path d="m9 6 6 6-6 6"/>',
  'chevron-left': '<path d="m15 6-6 6 6 6"/>',
  'arrow-left': '<path d="M19 12H5m0 0 6-6m-6 6 6 6"/>',
  'arrow-up-right': '<path d="M7 17 17 7M8 7h9v9"/>',
  sort: '<path d="M7 4v16m0 0-3-3m3 3 3-3M17 20V4m0 0-3 3m3-3 3 3"/>',
  trending: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
  shuffle: '<path d="M16 3h5v5M4 20 21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/>',
  repeat:
    '<path d="m17 2 4 4-4 4M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v1a4 4 0 0 1-4 4H3"/>',
  'repeat-one':
    '<path d="m17 2 4 4-4 4M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v1a4 4 0 0 1-4 4H3"/><path d="M11.5 10.5 13 9.5v5"/>',
  volume:
    '<path d="M11 5 6 9H3v6h3l5 4zM15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/>',
  'volume-low': '<path d="M11 5 6 9H3v6h3l5 4zM15.5 8.5a5 5 0 0 1 0 7"/>',
  'volume-mute': '<path d="M11 5 6 9H3v6h3l5 4zM22 9l-6 6M16 9l6 6"/>',
  lyrics: '<path d="M4 5h16v11H8l-4 4z"/><path d="M8 9h8M8 12h5"/>',
  queue: '<path d="M4 6h16M4 12h10M4 18h7"/><path d="M17 15v6l4-3z"/>',
  'play-next': '<path d="M4 6h10M4 12h10M4 18h6"/><path d="M17 9v6M14 12h6"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  monitor:
    '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  mic: '<rect x="9" y="2.5" width="6" height="12" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7"/>',
  'skip-back':
    '<path d="M12 5a7 7 0 1 1-6.32 4"/><path d="M8.3 5.7 5.5 9l3.6.8"/>',
  'skip-forward':
    '<path d="M12 5a7 7 0 1 0 6.32 4"/><path d="M15.7 5.7 18.5 9l-3.6.8"/>',
  gauge:
    '<path d="M4 15a8 8 0 1 1 16 0"/><path d="M12 15 15.5 10"/><path d="M4 15h.01M20 15h.01M12 5.5v.01"/>',
  check: '<path d="M5 12.5 10 17 19 7"/>',
  'check-circle':
    '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.8 2.7L16 9.8"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  retry:
    '<path d="M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.2L3 16M3 21v-5h5"/>',
  link: '<path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1 1M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1-1"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  zap: '<path d="M13 2 3 14h7l-1 8 10-12h-7z"/>',
  zip: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M10 7h2M10 10h2M10 13h2M9.5 16h3v3h-3z"/>',
  grip: '<circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/>',
  filter: '<path d="M4 5h16l-6 7.5V19l-4 2v-8.5z"/>',
  image:
    '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="m21 15-5-5-4 4-3-3-6 6"/>',
  instagram:
    '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><path d="M17 7h.01"/>',
  folder:
    '<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5H9l2 2h8.5A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5M12 16h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  more: '<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>',
  'more-vertical':
    '<circle cx="12" cy="5" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="12" cy="19" r="1.2"/>',
  minimize: '<path d="m6 9 6 6 6-6"/>',
  expand: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
  timer: '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2M9 2h6"/>',
  equalizer:
    '<path d="M4 20v-5M4 11V4M9.3 20v-9M9.3 7V4M14.7 20v-3M14.7 13V4M20 20v-7M20 9V4M2 15h4M7.3 7h4M12.7 17h4M18 9h4"/>',
  copy: '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
  pencil:
    '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
  sliders:
    '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M2 14h4M10 8h4M18 16h4"/>',
  disc: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  globe:
    '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  server:
    '<rect x="3" y="4" width="18" height="7" rx="1.5"/><rect x="3" y="13" width="18" height="7" rx="1.5"/><path d="M7 7.5h.01M7 16.5h.01"/>',
  'file-music':
    '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><circle cx="10.5" cy="16.5" r="1.8"/><path d="M12.3 16.5V11l3 1"/>',
  palette:
    '<path d="M12 3a9 9 0 1 0 0 18c1 0 1.6-.8 1.6-1.7 0-1.3-1-1.6-1-2.7 0-1 .8-1.6 1.8-1.6H17a4 4 0 0 0 4-4C21 6.5 17 3 12 3z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7.5" r="1"/>',
  keyboard:
    '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
  music:
    '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
  playlist:
    '<path d="M3 6h12M3 12h12M3 18h7"/><circle cx="17" cy="17" r="3"/><path d="M20 17V7l2-1"/>',
  // The same heart as the solid one under FILLED, drawn as an outline for
  // "not liked"; the solid one is "liked".
  'heart-outline':
    '<path d="M12 20s-7-4.4-9.2-8.6C1.2 8.2 3 4.5 6.6 4.5c2.1 0 3.6 1.2 5.4 3.1 1.8-1.9 3.3-3.1 5.4-3.1 3.6 0 5.4 3.7 3.8 6.9C19 15.6 12 20 12 20z"/>',
  tag: '<path d="M3 3h8l10 10-8 8L3 11z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  cookie:
    '<path d="M21 12a9 9 0 1 1-9-9 3 3 0 0 0 4 3 3 3 0 0 0 5 6z"/><path d="M8.5 9.5h.01M12 14h.01M8 15h.01M15 16h.01"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  'panel-left':
    '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
  sparkle:
    '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
  wand: '<path d="M4 20 15 9M14 4l1 2 2 1-2 1-1 2-1-2-2-1 2-1zM19 11l.7 1.3L21 13l-1.3.7L19 15l-.7-1.3L17 13l1.3-.7z"/>',
  // Distinct from FILLED.youtube (the regular YouTube box mark) - a ring
  // with a solid play triangle, closer to YouTube Music's own circular
  // logo (https://music.youtube.com/img/on_platform_logo_dark.svg).
  // Used only for the artist banner's platform links, never as a stand-in
  // for the regular YouTube icon elsewhere.
  'youtube-music':
    '<circle cx="12" cy="12" r="9"/><path d="M10 8.4v7.2l6.2-3.6z" fill="currentColor" stroke="none"/>',
}

export const FILLED = {
  play: '<path d="M7 4.5v15a1 1 0 0 0 1.5.86l12.5-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5z"/>',
  pause:
    '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
  prev: '<path d="M6 5h2v14H6zM20 5.5v13a.5.5 0 0 1-.8.4L9.5 12.4a.5.5 0 0 1 0-.8l9.7-6.5a.5.5 0 0 1 .8.4z"/>',
  next: '<path d="M16 5h2v14h-2zM4 5.5v13a.5.5 0 0 0 .8.4l9.7-6.5a.5.5 0 0 0 0-.8L4.8 5.1a.5.5 0 0 0-.8.4z"/>',
  youtube:
    '<path d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2 26 26 0 0 0 2 12a26 26 0 0 0 .4 4.8 2.5 2.5 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8A26 26 0 0 0 22 12a26 26 0 0 0-.4-4.8zM10 15V9l5.2 3z"/>',
  share:
    '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 10.7l6.8-4M8.6 13.3l6.8 4" stroke="currentColor" stroke-width="2"/>',
  spotify:
    '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm4.6 14.4a.62.62 0 0 1-.86.2c-2.35-1.44-5.3-1.76-8.79-.96a.62.62 0 1 1-.28-1.21c3.81-.87 7.08-.5 9.72 1.11.3.18.39.57.21.86zm1.23-2.73a.78.78 0 0 1-1.07.26c-2.69-1.65-6.79-2.13-9.97-1.16a.78.78 0 0 1-.45-1.49c3.63-1.1 8.15-.57 11.24 1.33.36.22.48.7.25 1.06zm.1-2.85C14.7 8.9 9.38 8.73 6.3 9.66a.94.94 0 1 1-.54-1.8c3.53-1.07 9.4-.86 13.12 1.34a.94.94 0 0 1-.95 1.62z"/>',
  deezer:
    '<rect x="3" y="14" width="3" height="6" rx="1"/><rect x="8" y="10" width="3" height="10" rx="1"/><rect x="13" y="6" width="3" height="14" rx="1"/><rect x="18" y="2" width="3" height="18" rx="1"/>',
  twitter:
    '<path d="M3 3l7.5 9.4L3.4 21H6l5.4-6.9L16.3 21H21l-7.8-9.8L20.6 3H18l-5 6.4L8.7 3H3z"/>',
  facebook:
    '<path d="M14 3.5h-1.6c-2.3 0-3.8 1.5-3.8 3.9V9.5H6.3v3.2h2.3V21h3.4v-8.3h2.6l.5-3.2h-3.1V7.7c0-.9.4-1.4 1.4-1.4H14z"/>',
  heart:
    '<path d="M12 20s-7-4.4-9.2-8.6C1.2 8.2 3 4.5 6.6 4.5c2.1 0 3.6 1.2 5.4 3.1 1.8-1.9 3.3-3.1 5.4-3.1 3.6 0 5.4 3.7 3.8 6.9C19 15.6 12 20 12 20z"/>',
}
