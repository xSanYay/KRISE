<template>
  <div class="home-view">

    <div class="hero animate-slide-up">
      <div class="hero-badge badge badge-primary">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        Multi-Agent AI Commerce
      </div>

      <h1 class="hero-title">
        Skip the search.<br />
        <span class="text-glow">Achieve the goal.</span>
      </h1>

      <p class="hero-subtitle">
        Krise Engine translates your goals into perfect product recommendations.
        Our AI challenges your assumptions, audits marketing claims, and finds you
        the best value — not just the cheapest price.
      </p>

      <div class="hero-features">
        <div class="feature-chip" v-for="f in features" :key="f">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          {{ f }}
        </div>
      </div>

      <button class="btn btn-primary btn-lg" @click="startNewSession" :disabled="loading">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
        {{ loading ? 'Starting...' : 'Start Conversation' }}
      </button>

      <p class="hero-hint">Try: "I need a laptop for outdoor engineering fieldwork" or "phone for rough use by kids"</p>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const sessionStore = useSessionStore()
const loading = ref(false)

const features = [
  'Goal-to-spec translation',
  'Reddit & YouTube sentiment',
  'Real-time price scraping',
  'Swipe to refine',
]

async function startNewSession() {
  loading.value = true
  try {
    const id = await sessionStore.startSession()
    if (id) {
      router.push({ name: 'session', params: { id } })
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.home-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 20px;
}

.hero {
  text-align: center;
  max-width: 720px;
  z-index: 1;
}

.hero-badge {
  margin-bottom: 24px;
}

.hero-title {
  font-size: clamp(40px, 8vw, 76px);
  font-weight: 700;
  line-height: 1.05;
  margin-bottom: 24px;
  letter-spacing: -2px;
}
.text-glow {
  color: var(--text-primary);
  text-shadow: 0 0 40px rgba(255, 255, 255, 0.3);
}

.hero-subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  line-height: 1.7;
  max-width: 560px;
  margin: 0 auto 28px;
}

.hero-features {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-bottom: 40px;
}
.feature-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
}
.feature-chip:hover {
  border-color: #555555;
  color: var(--text-primary);
}

.btn-lg {
  padding: 14px 32px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 14px;
}

.hero-hint {
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-muted);
  font-style: italic;
}

@media (max-width: 768px) {
  
  .hero-title {
    font-size: clamp(28px, 9vw, 42px);
    line-height: 1.2;
    margin-bottom: 16px;
  }
  
  .hero-subtitle {
    font-size: 15px;
    padding: 0 10px;
    margin-bottom: 24px;
  }

  .hero-features {
    gap: 8px;
    margin-bottom: 24px;
  }

  .feature-chip {
    font-size: 12px;
    padding: 5px 12px;
  }

  .btn-lg {
    width: 100%;
    max-width: 320px;
  }
}
</style>
