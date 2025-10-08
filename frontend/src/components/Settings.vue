<template>
  <!-- Put this part before </body> tag -->
  <input type="checkbox" id="my-modal" class="modal-toggle" />
  <div class="modal">
    <div class="modal-box relative">
      <label for="my-modal" class="btn btn-sm btn-circle absolute right-2 top-2"
        >✕</label
      >
      <h3 class="font-bold text-lg">Download Settings</h3>
      <div class="flex flex-col justify-center my-4">
        <!-- audio_provider -->
        <div class="form-control w-full">
          <label class="label">
            <span class="label-text">Audio Provider</span>
          </label>
          <select
            class="select w-full"
            v-model="sm.settings.value.audio_providers[0]"
          >
            <option
              v-for="(provider, index) in sm.settingsOptions.audio_providers"
              :key="index"
              :selected="provider === sm.settings.value.audio_providers?.[0]"
            >
              {{ provider }}
            </option>
          </select>
        </div>
        <!-- lyrics_provider -->
        <div class="form-control w-full">
          <label class="label">
            <span class="label-text">Lyrics Provider</span>
          </label>
          <select
            class="select w-full"
            v-model="sm.settings.value.lyrics_providers[0]"
          >
            <option
              v-for="(provider, index) in sm.settingsOptions.lyrics_providers"
              :key="index"
              :selected="provider === sm.settings.value.lyrics_providers?.[0]"
            >
              {{ provider }}
            </option>
          </select>
        </div>
        <!-- format -->
        <div class="form-control w-full">
          <label class="label">
            <span class="label-text">Output Format</span>
          </label>
          <select class="select w-full" v-model="sm.settings.value.format">
            <option
              v-for="(format, index) in sm.settingsOptions.format"
              :key="index"
              :selected="format === sm.settings.value.format"
            >
              {{ format }}
            </option>
          </select>
        </div>
      </div>
      <!-- Saved Changes alerts -->
      <div
        v-if="sm.isSaved.value === true"
        class="alert alert-success shadow-lg"
      >
        <div>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="stroke-current flex-shrink-0 h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>Changes saved</span>
        </div>
      </div>
      <div
        v-if="sm.isSaved.value === false"
        class="alert alert-error shadow-lg"
      >
        <div>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="stroke-current flex-shrink-0 h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>Error! Unable to save settings</span>
        </div>
      </div>
      <div class="modal-action">
        <label class="btn" @click="sm.saveSettings()">Save</label>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSettingsManager } from '../model/settings'

const sm = useSettingsManager()
</script>

<style scoped></style>
