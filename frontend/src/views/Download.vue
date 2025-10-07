<template>
  <div>
    <Navbar />
    <DownloadList />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import Navbar from '/src/components/Navbar.vue'
import DownloadList from '/src/components/DownloadList.vue'

export default {
  components: { Navbar, DownloadList },
  setup() {
    onMounted(() => {
      window.scroll(0, 0)
    })

    return {}
  },
}
</script>

<style scoped></style>
