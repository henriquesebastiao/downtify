import { afterEach, describe, expect, it, vi } from 'vitest'
import { AVAILABLE_LOCALES, currentLocale, setLocale, t } from '../i18n'

describe('Simplified Chinese locale', () => {
  afterEach(() => {
    setLocale('en')
    vi.unstubAllGlobals()
  })

  it('is available in the language menu', () => {
    expect(
      AVAILABLE_LOCALES.find((locale) => locale.code === 'zh-CN').name
    ).toBe('简体中文')
  })

  it('translates navigation, login and settings', () => {
    setLocale('zh-CN')
    expect(currentLocale.value).toBe('zh-CN')
    expect(t('nav.library')).toBe('音乐库')
    expect(t('auth.signInTitle')).toBe('登录 Downtify')
    expect(t('settings.language')).toBe('语言')
    expect(t('playlists.uploadCover')).toBe('上传封面')
  })

  it('formats Chinese counts, substitutions and punctuation', () => {
    setLocale('zh-CN')
    expect(t('common.tracks', { count: 1 })).toBe('1 首歌曲')
    expect(t('common.tracks', { count: 1200 })).toBe('1,200 首歌曲')
    expect(t('search.resultsFor', { query: '陈奕迅' })).toBe(
      '“陈奕迅”的搜索结果'
    )
    expect(t('monitor.everyHours', { count: 3 })).toBe('每 3 小时')
  })

  it('persists the selection and updates the document language', () => {
    const setItem = vi.fn()
    const setAttribute = vi.fn()
    vi.stubGlobal('localStorage', { setItem })
    vi.stubGlobal('document', { documentElement: { setAttribute } })
    setLocale('zh-CN')
    expect(setItem).toHaveBeenCalledWith('downtify-locale', 'zh-CN')
    expect(setAttribute).toHaveBeenCalledWith('lang', 'zh-CN')
  })
})
