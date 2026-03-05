<template>
  <div class="home-view">
    <!-- Background glow effects -->
    <div class="bg-glow glow-1"></div>
    <div class="bg-glow glow-2"></div>

    <div class="hero animate-slide-up">
      <div class="hero-badge badge badge-primary">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        Multi-Agent AI Commerce
      </div>

      <h1 class="hero-title">
        Stop searching for <span class="text-gradient">products</span>.<br />
        Start achieving <span class="text-gradient">goals</span>.
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

    <!-- Floating cards -->
    <div class="floating-cards">
      <div class="float-card glass" style="--delay: 0s; --x: -20px">
        <div class="float-card-text">Intent Mapping</div>
      </div>
      <div class="float-card glass" style="--delay: 1.5s; --x: 15px">
        <div class="float-card-text">Clarification</div>
      </div>
      <div class="float-card glass" style="--delay: 3s; --x: -10px">
        <div class="float-card-text">Sentiment Auditing</div>
      </div>
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

/* Background glows */
.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.15;
  pointer-events: none;
}
.glow-1 {
  width: 500px;
  height: 500px;
  background: #7c3aed;
  top: -10%;
  right: -5%;
}
.glow-2 {
  width: 400px;
  height: 400px;
  background: #06b6d4;
  bottom: -10%;
  left: -5%;
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
  font-size: clamp(32px, 5vw, 56px);
  font-weight: 800;
  line-height: 1.15;
  margin-bottom: 20px;
  letter-spacing: -1px;
}
.text-gradient {
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
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
  gap: 10px;
  margin-bottom: 32px;
}
.feature-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  color: #34d399;
  font-size: 13px;
  font-weight: 500;
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

/* Floating cards */
.floating-cards {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
}
.float-card {
  position: absolute;
  padding: 14px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  animation: float 5s ease-in-out infinite;
  animation-delay: var(--delay);
  opacity: 0.4;
}
.float-card:nth-child(1) { top: 15%; left: 8%; }
.float-card:nth-child(2) { top: 25%; right: 6%; }
.float-card:nth-child(3) { bottom: 20%; left: 12%; }
.float-card-text { font-size: 13px; color: var(--text-secondary); font-weight: 500; }

@media (max-width: 768px) {
  .floating-cards { display: none; }
  
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
