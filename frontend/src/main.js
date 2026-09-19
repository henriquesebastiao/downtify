import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index'

import './index.css'
import './model/theme'

createApp(App).use(router).mount('#app')
