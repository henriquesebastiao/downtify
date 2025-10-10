<template>
  <div>
    <Navbar />
    <Hero />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import Hero from '/src/components/Hero.vue'
import Navbar from '/src/components/Navbar.vue'
import API from '../model/api'

export default {
  components: { Navbar, Hero },
  setup() {
    onMounted(() => {
      window.scroll(0, 0)
    })
    return {}
  },
}
</script>

<style scoped></style>
