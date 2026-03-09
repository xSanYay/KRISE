import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

function parseCsv(value: string | undefined, fallback: string[]) {
  if (!value) return fallback

  const parsed = value.split(',').map((item) => item.trim()).filter(Boolean)
  return parsed.length > 0 ? parsed : fallback
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', '')
  const backendPort = env.APP_PORT || '8000'
  const allowedHosts = parseCsv(env.VITE_ALLOWED_HOSTS, [
    'localhost',
    '127.0.0.1',
    '.app.github.dev',
    '.github.dev',
  ])
  const backendHttpUrl = env.VITE_BACKEND_HTTP_URL || `http://localhost:${backendPort}`
  const backendWsUrl = env.VITE_BACKEND_WS_URL || `ws://localhost:${backendPort}`

  return {
    clearScreen: false,
    envDir: '..',
    plugins: [vue(), tailwindcss()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      allowedHosts,
      proxy: {
        '/api': {
          target: backendHttpUrl,
          changeOrigin: true,
        },
        '/ws': {
          target: backendWsUrl,
          ws: true,
        },
      },
    },
  }
})
