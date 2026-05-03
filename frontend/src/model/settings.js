import { ref, computed } from 'vue'

import API from '/src/model/api'

const settings = ref({
  audio_providers: [''],
  lyrics_providers: [''],
  download_lyrics: true,
  format: '',
  bitrate: '320',
  output: '',
  generate_m3u: true,
  organize_by_artist: false,
})

const settingsOptions = {
  audio_providers: ['youtube', 'youtube-music'],
  lyrics_providers: ['lrclib', 'genius', 'musixmatch', 'azlyrics'],
  format: ['mp3', 'flac', 'ogg', 'opus', 'm4a'],
  bitrate: ['128', '192', '256', '320'],
  output: '{artists} - {title}.{output-ext}',
}

API.getSettings().then((res) => {
  if (res.status === 200) {
    console.log('Received settings:', res.data)
    settings.value = res.data
  } else {
    console.log('Error loading settings')
  }
})

export function useSettingsManager() {
  const isSaved = ref()
  function saveSettings() {
    console.log('Saving settings:', settings.value)
    API.setSettings(settings.value).then((res) => {
      if (res.status === 200) {
        console.log('Saved!')
        isSaved.value = true
        setTimeout(() => {
          isSaved.value = null
        }, 2000)
      } else {
        console.error('Error saving settings.', res)
        isSaved.value = false
        setTimeout(() => {
          isSaved.value = null
        }, 2000)
      }
    })
  }
  return { saveSettings, settings, settingsOptions, isSaved }
}
