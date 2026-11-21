import Layout from './components/Layout.vue'
import EnglishOnly from './components/EnglishOnly.vue'
import Icon from './components/Icon.vue'
import HomeActions from './components/HomeActions.vue'
import HomeFeatures from './components/HomeFeatures.vue'
import HomeHighlights from './components/HomeHighlights.vue'
import HomePipeline from './components/HomePipeline.vue'
import HomeShowcase from './components/HomeShowcase.vue'
import './style.css'

export default {
  Layout,
  enhanceApp({ app }) {
    // Used from the Markdown pages.
    app.component('DocIcon', Icon)
    app.component('EnglishOnly', EnglishOnly)
    app.component('HomeActions', HomeActions)
    app.component('HomeFeatures', HomeFeatures)
    app.component('HomeHighlights', HomeHighlights)
    app.component('HomePipeline', HomePipeline)
    app.component('HomeShowcase', HomeShowcase)
  },
}
