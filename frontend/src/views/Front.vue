<template>
  <div>
    <NavbarFront />
    <Hero />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import Hero from '/src/components/Hero.vue'
import NavbarFront from '/src/components/NavbarFront.vue'
import API from '../model/api'

export default {
  components: { NavbarFront, Hero },
  setup() {
    onMounted(() => {
      window.scroll(0, 0)
    })
    return {}
  },
}
</script>

<style scoped></style>
