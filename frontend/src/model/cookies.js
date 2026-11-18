import { ref } from 'vue'

import API from '/src/model/api'

// Shape mirrors CookiesStore.status() in downtify/cookies.py.
const status = ref({
  configured: false,
  source: null,
  locked: false,
  path: null,
  size: null,
  updated_at: null,
  // Last keep-alive result (downtify/cookie_refresh.py).
  health: { state: 'unknown' },
})

const loading = ref(false)
const busy = ref(false)
const checking = ref(false)
const error = ref('')
const warnings = ref([])

function detailOf(err, fallback) {
  return err?.response?.data?.detail || fallback
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const res = await API.getCookiesStatus()
    status.value = res.data
  } catch (err) {
    error.value = detailOf(err, 'Could not load the cookie status.')
  } finally {
    loading.value = false
  }
}

async function upload(file) {
  busy.value = true
  error.value = ''
  warnings.value = []
  try {
    const res = await API.uploadCookies(file)
    const { warnings: uploadWarnings, ...rest } = res.data
    status.value = rest
    warnings.value = uploadWarnings || []
    // The server checks the new file in the background; pick it up.
    setTimeout(refresh, 5000)
    return true
  } catch (err) {
    error.value = detailOf(err, 'Could not upload the file.')
    return false
  } finally {
    busy.value = false
  }
}

async function remove() {
  busy.value = true
  error.value = ''
  warnings.value = []
  try {
    const res = await API.deleteCookies()
    const { deleted: _deleted, ...rest } = res.data
    status.value = rest
    return true
  } catch (err) {
    error.value = detailOf(err, 'Could not delete the file.')
    return false
  } finally {
    busy.value = false
  }
}

async function check() {
  checking.value = true
  error.value = ''
  try {
    const res = await API.checkCookies()
    status.value = res.data
  } catch (err) {
    error.value = detailOf(err, 'Could not check the cookies.')
  } finally {
    checking.value = false
  }
}

export function useCookiesManager() {
  return {
    status,
    loading,
    busy,
    checking,
    error,
    warnings,
    refresh,
    upload,
    remove,
    check,
  }
}
