<template>
  <!-- :data-theme="theme ? 'forest' : 'emerald'" -->
  <div class="bg-base-300 absolute w-full top-0">
    <router-view></router-view>
    <Footer />
    <Settings />
  </div>
</template>

<script setup>
import { onBeforeMount } from 'vue'
import Footer from './components/Footer.vue'
import Settings from './components/Settings.vue'
import { useBinaryThemeManager } from './model/theme'

const themeMgr = useBinaryThemeManager()
onBeforeMount(() => {
  themeMgr.setLightAlias('emerald')
  themeMgr.setDarkAlias('forest')
})
</script>

<style></style>
