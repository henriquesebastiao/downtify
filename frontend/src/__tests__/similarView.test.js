import { describe, expect, it, vi } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ replace: vi.fn() }),
}))

vi.mock('/src/model/api', () => ({
  default: {
    onUnauthorized: () => () => {},
    onForbidden: () => () => {},
    getAuthStatus: () =>
      Promise.resolve({ data: { signed_in: true, user: { role: 'admin' } } }),
    onMessage: () => () => {},
    getSettings: () => Promise.resolve({ data: {} }),
    lookupLibrarySongs: () => Promise.resolve({ data: [] }),
    getSimilarTracks: vi.fn(),
  },
}))

import SimilarView from '../views/SimilarView.vue'
import { setLocale } from '../i18n'

describe('SimilarView', () => {
  it('has a submit button so Enter submits the two-field form', async () => {
    setLocale('en')
    const html = await renderToString(createSSRApp(SimilarView))
    // Browsers only submit a form with more than one text field on Enter
    // when it has a submit button (HTML implicit submission).
    const form = html.match(/<form[^>]*>([\s\S]*?)<\/form>/)
    expect(form).not.toBeNull()
    expect(form[1].match(/<input/g)).toHaveLength(2)
    expect(form[1]).toMatch(/<button[^>]*type="submit"/)
  })
})
