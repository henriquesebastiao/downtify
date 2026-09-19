<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 28 28"
    class="shrink-0"
    role="img"
    aria-label="Downtify"
  >
    <circle cx="14" cy="14" r="14" class="fill-accent" />
    <path
      d="M9.5 8.2c3-.3 6-.3 9 0v3.1h2.6c.4 0 .6.3.5.6-1.5 5-5.5 9-7 10.4a.9.9 0 0 1-1.2 0C11.9 20.9 7.9 16.9 6.4 11.9c-.1-.3.1-.6.5-.6h2.6z"
      class="fill-bg"
    />
  </svg>
</template>

<script setup>
defineProps({ size: { type: Number, default: 28 } })
</script>
