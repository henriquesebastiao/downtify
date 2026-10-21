<template>
  <SettingGroup
    :title="t('visibility.title')"
    :description="t('visibility.hint')"
  >
    <p v-if="loaded && !total" class="px-5 py-4 text-sm text-muted">
      {{ t('visibility.none') }}
    </p>
    <template v-for="group in groups" :key="group.id">
      <template v-if="group.rows.length">
        <p class="eyebrow px-5 pt-4 pb-1">
          {{ t(`visibility.group.${group.id}`) }}
        </p>
        <ul class="flex flex-col">
          <li
            v-for="row in group.rows"
            :key="row.key"
            class="flex items-center gap-3 px-5 py-3"
          >
            <span
              class="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-2 text-muted"
              aria-hidden="true"
            >
              <AppIcon :name="group.icon" :size="18" />
            </span>
            <span class="flex min-w-0 flex-1 flex-col">
              <span class="truncate text-sm font-semibold">{{
                row.title
              }}</span>
              <span v-if="row.subtitle" class="truncate text-[12px] text-muted">
                {{ row.subtitle }}
              </span>
            </span>
            <UiButton
              variant="ghost"
              size="sm"
              icon="eye"
              :loading="busy === row.key"
              @click="showAgain(row)"
            >
              {{ t('visibility.show') }}
            </UiButton>
          </li>
        </ul>
      </template>
    </template>
  </SettingGroup>
</template>

<script setup>
// Settings > Users (admins): what's hidden from users, with a way to show
// each item again. Hiding itself happens in the Library. See
// downtify/library_visibility.py.
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
import SettingGroup from './SettingGroup.vue'
import API from '/src/model/api'
import { useUi } from '/src/model/ui'
import { useVisibility } from '/src/model/visibility'
import { hiddenGroups } from '/src/lib/visibility'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const ui = useUi()
const visibility = useVisibility()

const groups = ref([])
const loaded = ref(false)
const busy = ref('')

const total = computed(() =>
  groups.value.reduce((sum, group) => sum + group.rows.length, 0)
)

async function load() {
  try {
    groups.value = hiddenGroups((await API.getLibraryVisibility()).data)
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    loaded.value = true
  }
}

async function showAgain(row) {
  busy.value = row.key
  try {
    await visibility.change('show', [row.item])
    await load()
  } finally {
    busy.value = ''
  }
}

onMounted(load)
</script>
