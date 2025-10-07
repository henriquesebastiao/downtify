<template>
  <Hero />
</template>

<script>
import { ref, onMounted } from 'vue'
import Hero from '/src/components/Hero.vue'
import API from '../model/api'

export default {
  components: { Hero },
  setup() {
    onMounted(() => {
      window.scroll(0, 0)
    })
    return {}
  },
}
</script>

<style scoped></style>
