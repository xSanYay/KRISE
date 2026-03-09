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

      <div class="mode-grid">
        <article class="mode-card glass-lg">
          <div class="mode-tag">Default</div>
          <h2>Shopping Advisor</h2>
          <p>Translate goals into specs, clarify needs, then move into recommendation and swipe mode.</p>
          <button class="btn btn-primary btn-lg" @click="startNewSession('standard')" :disabled="loadingMode !== null">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
            {{ loadingMode === 'standard' ? 'Starting...' : 'Start Conversation' }}
          </button>
          <p class="mode-hint">Try: "I need a laptop for outdoor engineering fieldwork"</p>
        </article>

        <article class="mode-card decision-card glass-lg">
          <h2>Socratic Friction Agent</h2>
          <p>Decision-only chat mode that challenges your reasoning, tests tradeoffs, and ends with a verdict.</p>
          <ul class="mode-points">
            <li>Clarify what you actually need</li>
            <li>Pressure-test impulse vs conviction</li>
          </ul>
          <button class="btn btn-primary btn-lg decision-btn" @click="startNewSession('socratic_decision')" :disabled="loadingMode !== null">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v18"/><path d="M3 12h18"/></svg>
            {{ loadingMode === 'socratic_decision' ? 'Opening...' : 'Start Friction Mode' }}
          </button>
          <p class="mode-hint">Try: "I am confused between Samsung Watch 8 and Pixel Watch 4"</p>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import type { SessionMode } from '@/lib/api'

const router = useRouter()
const sessionStore = useSessionStore()
const loadingMode = ref<SessionMode | null>(null)

const features = [
  'Goal-to-spec translation',
  'Reddit & YouTube sentiment',
  'Real-time price scraping',
  'Swipe to refine',
]

async function startNewSession(mode: SessionMode) {
  loadingMode.value = mode
  try {
    const id = await sessionStore.startSession('en', mode)
    if (id) {
      router.push({ name: 'session', params: { id } })
    }
  } finally {
    loadingMode.value = null
  }
}
</script>

<style scoped>
.home-view {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  position: relative;
  overflow: visible;
  padding: 32px 24px 48px;
}

.hero {
  text-align: center;
  width: min(1180px, 100%);
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
  margin: 0 auto 22px;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(420px, 1fr));
  gap: 24px;
  margin: 8px auto 0;
  max-width: 1100px;
  text-align: left;
  align-items: stretch;
}

.mode-card {
  min-height: 320px;
  padding: 28px 30px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.08), transparent 35%),
    var(--bg-card);
}

.decision-card {
  background:
    radial-gradient(circle at top left, rgba(209, 255, 115, 0.08), transparent 38%),
    linear-gradient(180deg, rgba(21, 29, 14, 0.9), rgba(10, 12, 8, 0.98));
  border-color: rgba(209, 255, 115, 0.16);
}

.mode-tag {
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.mode-card h2 {
  font-size: 26px;
  line-height: 1.1;
}

.mode-card p {
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.6;
}

.mode-points {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.5;
}

.mode-points li {
  padding-left: 16px;
  position: relative;
}

.mode-points li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 9px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d1ff73;
}

.decision-btn {
  background: #d1ff73;
  border-color: #d1ff73;
  color: #081106;
}

.decision-btn:hover {
  background: #defb98;
  box-shadow: 0 8px 28px rgba(209, 255, 115, 0.2);
}

.mode-hint {
  margin-top: auto;
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}

.hero-features {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-bottom: 28px;
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
  
  .home-view {
    padding: 20px 16px 32px;
  }

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

  .mode-grid {
    grid-template-columns: 1fr;
    max-width: 620px;
    gap: 16px;
  }

  .mode-card {
    padding: 20px;
    min-height: unset;
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
