import Layout from './components/Layout.vue'
import Icon from './components/Icon.vue'
import HomeActions from './components/HomeActions.vue'
import HomeHighlights from './components/HomeHighlights.vue'
import HomePipeline from './components/HomePipeline.vue'
import './style.css'

export default {
  Layout,
  enhanceApp({ app }) {
    // Used from the Markdown pages.
    app.component('DocIcon', Icon)
    app.component('HomeActions', HomeActions)
    app.component('HomeHighlights', HomeHighlights)
    app.component('HomePipeline', HomePipeline)
  },
}
