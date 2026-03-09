<template>
  <header class="app-header glass">
    <div class="header-inner">
      <router-link to="/" class="logo">
        <img v-if="showLogo" class="logo-image" :src="logoSrc" alt="Krise logo" @error="handleLogoError" />
        <span class="logo-text">Krise</span>
        <span class="logo-badge">engine</span>
      </router-link>

      <div class="header-right">
        <div v-if="sessionStore.sessionId" class="conviction-pill">
          <div class="conviction-dot" :style="{ background: convictionColor }"></div>
          <span>{{ Math.round(sessionStore.convictionScore * 100) }}% conviction</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()
const showLogo = ref(true)
const logoSrc = '/logo.png'

const convictionColor = computed(() => {
  const s = sessionStore.convictionScore
  if (s >= 0.8) return '#10b981'
  if (s >= 0.5) return '#f59e0b'
  return '#ef4444'
})

function handleLogoError() {
  showLogo.value = false
}
</script>

<style scoped>
.app-header {
  position: relative;
  z-index: 50;
  border-bottom: 1px solid var(--border-color);
  border-radius: 0;
}
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  max-width: 1400px;
  margin: 0 auto;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
}
.logo-image {
  width: 28px;
  height: 28px;
  object-fit: contain;
  flex-shrink: 0;
}
.logo-text {
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 22px;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.logo-badge {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
  padding: 2px 8px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.conviction-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--bg-glass);
  border: 1px solid var(--border-color);
  font-size: 13px;
  color: var(--text-secondary);
}
.conviction-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
</style>
