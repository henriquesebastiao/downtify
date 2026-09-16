import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// The backend's own routes, proxied during `npm run dev` so the SPA
// can be developed against `make run` on :8000.
const BACKEND = process.env.DOWNTIFY_DEV_BACKEND || 'http://127.0.0.1:8000'
const backendRoutes = [
  '/api',
  '/list',
  '/tracks',
  '/playlists',
  '/media',
  '/cover',
  '/lyrics',
  '/delete',
  '/downloads',
]

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  define: {
    'process.env': {},
  },
  build: {
    rollupOptions: {
      output: {
        // Framework code and translations change rarely — keep them in
        // their own long-cached chunks.
        manualChunks(id) {
          if (id.includes('node_modules')) return 'vendor'
          if (id.includes('/src/i18n/')) return 'i18n'
        },
      },
    },
  },
  server: {
    proxy: Object.fromEntries(
      backendRoutes.map((route) => [
        route,
        { target: BACKEND, changeOrigin: true, ws: route === '/api' },
      ])
    ),
  },
})
