import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index'
import { localeReady } from './i18n'

import './index.css'
import './model/theme'

// Mounted once the saved language is in (a few kB, fetched on its own),
// so the first paint is already in it - English if it can't be fetched.
localeReady.finally(() => createApp(App).use(router).mount('#app'))
