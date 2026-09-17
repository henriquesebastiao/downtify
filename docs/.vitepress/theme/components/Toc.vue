<template>
  <nav v-if="headers.length" aria-labelledby="toc-title" class="text-[13px]">
    <p id="toc-title" class="eyebrow mb-3">On this page</p>
    <ul class="flex flex-col border-l border-line-2">
      <li v-for="header in headers" :key="header.id">
        <a
          :href="`#${header.id}`"
          class="-ml-px block border-l py-1 leading-snug transition-colors"
          :class="[
            header.level === 3 ? 'pl-6' : 'pl-3.5',
            active === header.id
              ? 'border-accent font-semibold text-fg'
              : 'border-transparent text-muted hover:text-fg',
          ]"
          :aria-current="active === header.id ? 'location' : undefined"
          >{{ header.title }}</a
        >
      </li>
    </ul>
  </nav>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { onContentUpdated } from 'vitepress'

const headers = ref([])
const active = ref('')
// Top bar height plus a little breathing room.
const OFFSET = 96

function collect() {
  headers.value = [...document.querySelectorAll('.doc :is(h2, h3)[id]')].map(
    (el) => ({
      id: el.id,
      level: Number(el.tagName[1]),
      title: el.textContent.replace(/[​\s]+$/g, '').trim(),
    })
  )
  update()
}

function update() {
  let current = ''
  for (const { id } of headers.value) {
    const el = document.getElementById(id)
    if (el && el.getBoundingClientRect().top - OFFSET <= 1) current = id
    else break
  }
  const atBottom =
    window.innerHeight + window.scrollY >= document.body.scrollHeight - 2
  if (atBottom && headers.value.length) {
    current = headers.value[headers.value.length - 1].id
  }
  active.value = current
}

let frame = 0
function onScroll() {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(update)
}

onContentUpdated(collect)
onMounted(() => {
  collect()
  window.addEventListener('scroll', onScroll, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>
