<template>
  <div class="not-doc flex flex-wrap gap-2.5">
    <ButtonLink v-for="action in actions" :key="action.link" v-bind="action" />
  </div>
</template>

<script setup>
import ButtonLink from './ButtonLink.vue'

defineProps({ actions: { type: Array, required: true } })
</script>
