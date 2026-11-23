<template>
  <!-- The saved channels, not an empty form that fills in a moment later. -->
  <UiPanelSkeleton v-if="!loaded" :rows="4" />
  <SettingGroup
    v-else
    class="animate-reveal"
    :title="t('notify.title')"
    :description="t('notify.hint')"
  >
    <SettingRow
      :label="t('notify.enabled')"
      :description="t('notify.enabledHint')"
    >
      <UiSwitch v-model="form.enabled" :aria-label="t('notify.enabled')" />
    </SettingRow>
    <SettingRow
      :label="t('notify.progressEvery')"
      :description="t('notify.progressEveryHint')"
      stacked
    >
      <UiSegmented
        v-model="form.progress_seconds"
        :options="progressOptions"
        show-labels
      />
    </SettingRow>
  </SettingGroup>

  <SettingGroup
    v-for="name in CHANNELS"
    :key="name"
    :title="t(`notify.channel_${name}`)"
    :description="t(`notify.channel_${name}Hint`)"
  >
    <SettingRow :label="t('notify.channelOn')">
      <UiSwitch
        v-model="form.channels[name].enabled"
        :aria-label="t(`notify.channel_${name}`)"
      />
    </SettingRow>

    <template v-if="form.channels[name].enabled">
      <!-- Discord: a webhook only posts; a bot also answers commands. -->
      <template v-if="name === 'discord'">
        <SettingRow
          :label="t('notify.discordMode')"
          :description="t('notify.discordModeHint')"
          stacked
        >
          <UiSegmented
            v-model="form.channels.discord.mode"
            :options="modeOptions"
            show-labels
          />
        </SettingRow>
        <SettingRow
          v-if="form.channels.discord.mode === 'webhook'"
          :label="t('notify.webhookUrl')"
          :description="t('notify.webhookUrlHint')"
          stacked
        >
          <SecretField
            channel="discord"
            secret="webhook_url"
            :label="t('notify.webhookUrl')"
          />
        </SettingRow>
        <template v-else>
          <SettingRow
            :label="t('notify.botToken')"
            :description="t('notify.botTokenHint')"
            stacked
          >
            <SecretField
              channel="discord"
              secret="bot_token"
              :label="t('notify.botToken')"
            />
          </SettingRow>
          <SettingRow
            :label="t('notify.channelId')"
            :description="t('notify.channelIdHint')"
            stacked
          >
            <UiInput
              v-model.trim="form.channels.discord.channel_id"
              :aria-label="t('notify.channelId')"
              class="w-full"
              inputmode="numeric"
              mono
              placeholder="123456789012345678"
            />
          </SettingRow>
          <SettingRow
            :label="t('notify.commands')"
            :description="t('notify.commandsHint')"
          >
            <UiSwitch
              v-model="form.channels.discord.commands"
              :aria-label="t('notify.commands')"
            />
          </SettingRow>
          <SettingRow
            v-if="form.channels.discord.commands"
            :label="t('notify.allowedUsers')"
            :description="t('notify.allowedUsersHint')"
            stacked
          >
            <UiInput
              v-model="form.channels.discord.allowed_users"
              :aria-label="t('notify.allowedUsers')"
              class="w-full"
              mono
              placeholder="123456789012345678 234567890123456789"
            />
          </SettingRow>
          <SettingRow
            v-if="form.channels.discord.commands"
            :label="t('notify.botState')"
            stacked
          >
            <div class="flex w-full flex-col gap-2 text-[13px]">
              <p class="flex items-center gap-2 text-fg-2" aria-live="polite">
                <UiBadge :tone="botTone">{{
                  t(`notify.bot_${bot.state || 'off'}`)
                }}</UiBadge>
                <span v-if="bot.user">{{ bot.user }}</span>
              </p>
              <p v-if="bot.error" class="text-danger" role="alert">
                {{ bot.error }}
              </p>
              <a
                v-if="bot.invite_url"
                :href="bot.invite_url"
                target="_blank"
                rel="noopener"
                class="self-start text-accent underline"
                >{{ t('notify.invite') }}</a
              >
              <p class="text-muted">{{ t('notify.commandList') }}</p>
              <ul class="flex flex-wrap gap-1.5">
                <li
                  v-for="command in bot.commands || []"
                  :key="command"
                  class="rounded-md bg-surface-2 px-2 py-0.5 font-mono text-[12px] text-fg-2"
                >
                  /{{ command }}
                </li>
              </ul>
            </div>
          </SettingRow>
        </template>
      </template>

      <template v-else-if="name === 'ntfy'">
        <SettingRow :label="t('notify.server')" stacked>
          <UiInput
            v-model.trim="form.channels.ntfy.server"
            :aria-label="t('notify.server')"
            class="w-full"
            placeholder="https://ntfy.sh"
          />
        </SettingRow>
        <SettingRow
          :label="t('notify.topic')"
          :description="t('notify.topicHint')"
          stacked
        >
          <UiInput
            v-model.trim="form.channels.ntfy.topic"
            :aria-label="t('notify.topic')"
            class="w-full"
            mono
            placeholder="downtify-…"
          />
        </SettingRow>
        <SettingRow
          :label="t('notify.accessToken')"
          :description="t('notify.optional')"
          stacked
        >
          <SecretField
            channel="ntfy"
            secret="token"
            :label="t('notify.accessToken')"
          />
        </SettingRow>
      </template>

      <template v-else-if="name === 'gotify'">
        <SettingRow :label="t('notify.server')" stacked>
          <UiInput
            v-model.trim="form.channels.gotify.server"
            :aria-label="t('notify.server')"
            class="w-full"
            placeholder="https://gotify.example.com"
          />
        </SettingRow>
        <SettingRow
          :label="t('notify.appToken')"
          :description="t('notify.appTokenHint')"
          stacked
        >
          <SecretField
            channel="gotify"
            secret="token"
            :label="t('notify.appToken')"
          />
        </SettingRow>
      </template>

      <template v-else>
        <SettingRow
          :label="t('notify.webhookUrl')"
          :description="t('notify.genericHint')"
          stacked
        >
          <SecretField
            channel="webhook"
            secret="url"
            :label="t('notify.webhookUrl')"
          />
        </SettingRow>
      </template>

      <SettingRow
        :label="t('notify.what')"
        :description="t('notify.whatHint')"
        stacked
      >
        <div class="flex w-full flex-col gap-3">
          <div v-for="group in GROUPS" :key="group.list">
            <p class="mb-1.5 text-[12px] font-medium text-muted">
              {{ t(`notify.group_${group.list}`) }}
            </p>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="item in view?.[group.list] || []"
                :key="item"
                type="button"
                class="inline-flex h-8 items-center rounded-full px-3 text-[13px] font-medium transition-colors"
                :class="
                  form.channels[name][group.list].includes(item)
                    ? 'bg-fg text-bg'
                    : 'bg-surface-2 text-fg-3 hover:bg-raised'
                "
                :aria-pressed="form.channels[name][group.list].includes(item)"
                @click="toggle(name, group.list, item)"
              >
                {{ t(`notify.${group.prefix}_${item}`) }}
              </button>
            </div>
          </div>
        </div>
      </SettingRow>

      <SettingRow :label="t('notify.test')" :description="t('notify.testHint')">
        <UiButton
          variant="ghost"
          icon="bell"
          :loading="testing === name"
          :disabled="!!testing || !ready(name)"
          @click="sendTest(name)"
        >
          {{ t('notify.sendTest') }}
        </UiButton>
      </SettingRow>
      <p
        v-if="view?.errors?.[name]"
        class="px-5 pb-4 text-[13px] text-pretty text-danger"
        role="alert"
      >
        {{ t('notify.lastError', { error: view.errors[name] }) }}
      </p>
    </template>
  </SettingGroup>

  <div v-if="loaded" class="flex items-center gap-3">
    <UiButton :loading="saving" :disabled="saving || !dirty" @click="save">
      {{ t('notify.save') }}
    </UiButton>
    <span v-if="dirty" class="text-[13px] text-muted">{{
      t('notify.unsaved')
    }}</span>
  </div>
</template>

<script setup>
// Settings > Notifications (admins): Discord (webhook or bot with slash
// commands), ntfy, Gotify and a generic webhook, each with what to
// send. See downtify/notifications.py and notification_routes.py.
import { computed, defineComponent, h, onMounted, onUnmounted, ref } from 'vue'
import UiBadge from '../ui/UiBadge.vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import UiSegmented from '../ui/UiSegmented.vue'
import UiSwitch from '../ui/UiSwitch.vue'
import UiPanelSkeleton from '../ui/UiPanelSkeleton.vue'
import SettingGroup from './SettingGroup.vue'
import SettingRow from './SettingRow.vue'
import API from '/src/model/api'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'
import {
  channelReady,
  formFrom,
  savePayload,
  secretSaved,
  toggled,
} from '/src/lib/notifications'

const CHANNELS = ['discord', 'ntfy', 'gotify', 'webhook']
const GROUPS = [
  { list: 'tasks', prefix: 'task' },
  { list: 'phases', prefix: 'phase' },
  { list: 'events', prefix: 'event' },
]

const { t } = useI18n()
const ui = useUi()

const view = ref(null)
const form = ref(formFrom(emptySettings()))
const clear = ref([])
const saved = ref('')
const saving = ref(false)
const loaded = ref(false)
const testing = ref('')
let timer = null

function emptySettings() {
  const channels = {}
  for (const name of CHANNELS) {
    channels[name] = { enabled: false, tasks: [], phases: [], events: [] }
  }
  channels.discord.mode = 'webhook'
  return { enabled: false, progress_seconds: 60, channels }
}

const bot = computed(() => view.value?.bot || {})
const botTone = computed(
  () =>
    ({ connected: 'accent', error: 'danger', connecting: 'warn' })[
      bot.value.state
    ] || 'neutral'
)
const dirty = computed(
  () => JSON.stringify(savePayload(form.value, clear.value)) !== saved.value
)

function seconds(value) {
  return value < 60 ? `${value} s` : `${value / 60} min`
}
const progressOptions = computed(() =>
  (view.value?.progress_choices || [30, 60, 300, 900]).map((value) => ({
    value,
    label: seconds(value),
  }))
)
const modeOptions = computed(() => [
  { value: 'webhook', label: t('notify.modeWebhook') },
  { value: 'bot', label: t('notify.modeBot') },
])

function isSaved(channel, secret) {
  return secretSaved(view.value?.settings, clear.value, channel, secret)
}

function ready(name) {
  const flags = {}
  for (const key of ['webhook_url', 'bot_token', 'token', 'url']) {
    flags[`${key}_set`] = isSaved(name, key)
  }
  return channelReady(name, form.value.channels[name], flags)
}

function toggle(name, list, item) {
  const ch = form.value.channels[name]
  ch[list] = toggled(ch[list], item)
}

// A secret input: blank shows whether one is saved; typing replaces it.
const SecretField = defineComponent({
  props: { channel: String, secret: String, label: String },
  setup(props) {
    return () => {
      const ch = form.value.channels[props.channel]
      const has = isSaved(props.channel, props.secret)
      const key = `${props.channel}.${props.secret}`
      return h('div', { class: 'flex w-full flex-wrap items-center gap-2' }, [
        h(UiInput, {
          class: 'min-w-0 flex-1',
          type: 'password',
          ariaLabel: props.label,
          mono: true,
          modelValue: ch[props.secret],
          placeholder: has ? t('notify.secretSaved') : '',
          'onUpdate:modelValue': (value) => {
            ch[props.secret] = String(value || '').trim()
            clear.value = clear.value.filter((item) => item !== key)
          },
        }),
        has
          ? h(
              UiButton,
              {
                variant: 'ghost',
                icon: 'trash',
                onClick: () => {
                  ch[props.secret] = ''
                  clear.value = [...clear.value, key]
                },
              },
              () => t('notify.remove')
            )
          : null,
      ])
    }
  },
})

function errorOf(err) {
  const detail = err?.response?.data?.detail
  return detail?.message || detail?.code || t('toast.actionFailed')
}

function apply(data, { keepForm = false } = {}) {
  view.value = data
  if (keepForm) return
  form.value = formFrom(data.settings)
  clear.value = []
  saved.value = JSON.stringify(savePayload(form.value, clear.value))
}

async function load(options) {
  try {
    apply((await API.getNotifications()).data, options)
  } catch {
    // Leave the form as it is; the next refresh tries again.
  } finally {
    loaded.value = true
  }
}

async function save() {
  saving.value = true
  try {
    apply(
      (await API.saveNotifications(savePayload(form.value, clear.value))).data
    )
    ui.toast(t('notify.saved'), { kind: 'success' })
  } catch (err) {
    ui.toast(errorOf(err), { kind: 'error' })
  } finally {
    saving.value = false
  }
}

async function sendTest(name) {
  testing.value = name
  try {
    await API.testNotification(name, form.value.channels[name])
    ui.toast(t('notify.testSent'), { kind: 'success' })
  } catch (err) {
    ui.toast(t('notify.testFailed', { error: errorOf(err) }), {
      kind: 'error',
    })
  } finally {
    testing.value = ''
  }
}

onMounted(() => {
  load()
  // The bot's state and the last errors change on their own.
  timer = setInterval(() => load({ keepForm: true }), 10000)
})
onUnmounted(() => clearInterval(timer))
</script>
