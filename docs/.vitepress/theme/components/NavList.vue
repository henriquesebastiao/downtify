<template>
  <nav aria-label="Documentation" class="flex flex-col gap-0.5">
    <template v-for="(entry, index) in sidebar" :key="entry.title">
      <div v-if="entry.items" class="mt-5 mb-1 first:mt-0">
        <p class="eyebrow px-3 pb-1.5">{{ entry.title }}</p>
        <ul class="flex flex-col gap-0.5">
          <li v-for="item in entry.items" :key="item.page">
            <NavLink :item="item" />
          </li>
        </ul>
      </div>
      <NavLink
        v-else
        :item="entry"
        :class="index && sidebar[index - 1].items ? 'mt-4' : ''"
      />
    </template>
  </nav>
</template>

<script setup>
import { defineComponent, h } from 'vue'
import { withBase } from 'vitepress'
import Icon from './Icon.vue'
import { useNav } from '../composables/nav'

const { sidebar, isActive } = useNav()

const NavLink = defineComponent({
  props: { item: { type: Object, required: true } },
  setup(props) {
    return () => {
      const active = isActive(props.item)
      return h(
        'a',
        {
          href: withBase(props.item.link),
          'aria-current': active ? 'page' : undefined,
          class: [
            'flex h-9 items-center gap-3 rounded-control px-3 text-sm transition-colors',
            active
              ? 'bg-surface-2 font-semibold text-fg'
              : 'font-medium text-muted hover:bg-surface-2/60 hover:text-fg',
          ],
        },
        [
          h(Icon, {
            name: props.item.icon,
            size: 17,
            class: active ? 'text-accent' : '',
          }),
          h('span', { class: 'truncate' }, props.item.title),
        ]
      )
    }
  },
})
</script>
