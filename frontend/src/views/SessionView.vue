<template>
  <div class="session-view">
    <!-- Left panel: Chat -->
    <div class="chat-panel">
      <div v-if="sessionStore.isDecisionMode" class="decision-mode-strip">
        <div>
          <p class="decision-mode-label">Socratic Friction Agent</p>
          <h2>Pressure-test the purchase before you justify it.</h2>
        </div>
        <div class="decision-progress-chip" :class="{ complete: sessionStore.decisionComplete }">
          <span>{{ decisionProgressLabel }}</span>
        </div>
      </div>

      <div class="chat-messages" ref="messagesContainer">
        <ChatMessage
          v-for="(msg, i) in sessionStore.messages"
          :key="i"
          :msg="msg"
          @widget-submit="handleWidgetSubmit"
        />

        <!-- Loading Indicator -->
        <div v-if="sessionStore.isLoading" class="typing-container animate-fade-in">
          <div class="typing-indicator">
            <div class="typing-avatar">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              </svg>
            </div>
            <div class="typing-dots">
              <span class="dot" style="animation-delay: 0s"></span>
              <span class="dot" style="animation-delay: 0.2s"></span>
              <span class="dot" style="animation-delay: 0.4s"></span>
            </div>
          </div>
          <!-- Progress steps stream -->
          <div v-if="sessionStore.progressSteps.length > 0" class="search-progress">
            <div class="search-progress-steps">
              <div v-for="(step, i) in sessionStore.progressSteps" :key="i" class="step" :class="{ active: i === sessionStore.progressSteps.length - 1 }">
                <span class="step-dot" :style="{ opacity: i === sessionStore.progressSteps.length - 1 ? 1 : 0.4 }"></span>
                <span class="step-text">{{ step }}</span>
              </div>
            </div>
          </div>
          <div v-else class="search-progress">
            <div class="search-progress-steps">
              <div class="step active" :key="'s1'">
                <span class="step-dot"></span>
                <span class="step-text">{{ progressLabel }}</span>
              </div>
            </div>
            <div class="search-progress-bar">
              <div class="search-progress-fill"></div>
            </div>
          </div>
        </div>

      </div>

      <div v-if="showDecisionOnboarding" class="decision-onboarding">
        <div class="decision-onboarding-card glass-lg animate-slide-up">
          <div class="decision-onboarding-copy">
            <span class="decision-kicker">Decision setup</span>
            <h3>State the purchase decision exactly as it lives in your head.</h3>
            <p>
              Examples: “I am confused between Samsung Watch 8 and Pixel Watch 4” or
              “I want 4K video, but I am not sure it is worth the battery hit.”
            </p>
          </div>

          <form class="decision-onboarding-form" @submit.prevent="handleInitialStatement">
            <textarea
              v-model="initialStatementDraft"
              class="decision-textarea"
              rows="5"
              placeholder="Write the decision you want stress-tested..."
            />
            <button class="btn btn-primary btn-lg decision-submit" :disabled="!initialStatementDraft.trim() || sessionStore.isLoading">
              {{ sessionStore.isLoading ? 'Starting...' : 'Enter Friction Mode' }}
            </button>
          </form>
        </div>
      </div>

      <!-- Reshow Button (floats above chat messages when hidden) -->
      <div v-if="!sessionStore.isDecisionMode && sessionStore.hasProducts && isProductsHidden" class="reshow-products-bar animate-fade-in">
        <button class="btn btn-primary shadow-glow" @click="isProductsHidden = false">
          Resume Recommendations ({{ sessionStore.products.length }} left)
        </button>
      </div>

      <!-- Full-panel Swipe Deck Overlay -->
      <div v-if="!sessionStore.isDecisionMode && sessionStore.hasProducts && !isProductsHidden" class="products-overlay animate-slide-up">
        <div class="products-overlay-header">
          <div style="display: flex; align-items: center; gap: 16px;">
            <h2 class="overlay-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              Your Recommendations
            </h2>
            <span class="badge badge-primary">{{ sessionStore.products.length }} left</span>
          </div>
          <button class="btn btn-ghost close-overlay-btn" @click="isProductsHidden = true">
            Back to Chat
          </button>
        </div>
        <div class="products-overlay-content">
          <SwipeDeck
            :products="sessionStore.products"
            :shortlist-count="sessionStore.shortlist.length"
            @swipe="handleProductSwipe"
          />
        </div>
      </div>

      <!-- Mobile toggle button -->
      <div v-if="isMobile" class="mobile-toggle-bar glass">
        <button class="btn btn-ghost" @click="showMobilePanel = !showMobilePanel">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6" v-if="!showMobilePanel" />
            <polyline points="15 18 9 12 15 6" v-else />
          </svg>
          {{ mobilePanelLabel }}
        </button>
      </div>

      <ChatInput
        :disabled="isInputDisabled"
        :placeholder="inputPlaceholder"
        @send="handleSend"
      />
    </div>

    <!-- Right Side: Intent Profile / Recommendations -->
    <div class="side-panel" :class="{ 'mobile-open': showMobilePanel }">
      <!-- Mobile Close Button -->
      <div v-if="isMobile" style="padding: 16px; border-bottom: 1px solid var(--border-color); text-align: right;">
        <button class="btn btn-ghost" @click="showMobilePanel = false">
          Close
        </button>
      </div>

      <template v-if="sessionStore.isDecisionMode">
        <div class="profile-panel decision-panel">
          <div class="profile-header">
            <h3>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20"/><path d="M2 12h20"/></svg>
              Decision Audit
            </h3>
            <span class="badge" :class="decisionVerdictBadgeClass">{{ decisionStatusLabel }}</span>
          </div>

          <div class="decision-rail">
            <div class="decision-rail-top">
              <span>Progress</span>
              <span>{{ sessionStore.decisionTurn }}/{{ sessionStore.decisionMaxTurns }}</span>
            </div>
            <div class="progress-bar"><div class="fill" :style="{ width: decisionProgressWidth }"></div></div>
            <p class="decision-stage-copy">{{ decisionStageCopy }}</p>
          </div>

          <div v-if="sessionStore.decisionOutcome" class="decision-outcome-card">
            <div class="decision-outcome-head">
              <span class="decision-verdict">{{ sessionStore.decisionOutcome.verdict }}</span>
              <span class="badge badge-primary">Final</span>
            </div>
            <p class="decision-outcome-text">{{ sessionStore.decisionOutcome.rationale }}</p>
            <div class="decision-action-block">
              <span class="label">Recommended next step</span>
              <p>{{ sessionStore.decisionOutcome.recommendation }}</p>
            </div>
            <div class="decision-action-block">
              <span class="label">Non-consumer alternative</span>
              <p>{{ sessionStore.decisionOutcome.non_consumer_alternative }}</p>
            </div>
            <div v-if="sessionStore.decisionOutcome.key_tradeoffs.length > 0" class="decision-tradeoffs">
              <span class="label">Tradeoffs surfaced</span>
              <div v-for="(tradeoff, i) in sessionStore.decisionOutcome.key_tradeoffs" :key="i" class="ambiguity-item badge badge-warning">
                {{ tradeoff }}
              </div>
            </div>
          </div>

          <div v-if="sessionStore.intentProfile" class="profile-content">
            <div v-if="sessionStore.initialStatement" class="profile-item profile-item-stack">
              <span class="label">Decision</span>
              <span class="value decision-statement">{{ sessionStore.initialStatement }}</span>
            </div>
            <div v-if="sessionStore.intentProfile.primary_use_case" class="profile-item">
              <span class="label">Use Case</span>
              <span class="value">{{ sessionStore.intentProfile.primary_use_case }}</span>
            </div>
            <div v-if="sessionStore.intentProfile.product_category" class="profile-item">
              <span class="label">Category</span>
              <span class="value">{{ sessionStore.intentProfile.product_category }}</span>
            </div>
            <div v-if="sessionStore.intentProfile.constraints.budget_max" class="profile-item">
              <span class="label">Budget</span>
              <span class="value">₹{{ Number(sessionStore.intentProfile.constraints.budget_max).toLocaleString('en-IN') }}</span>
            </div>
            <div class="conviction-meter">
              <div class="conviction-label">
                <span>Clarity</span>
                <span class="conviction-value" :style="{ color: convictionColor }">
                  {{ Math.round(sessionStore.convictionScore * 100) }}%
                </span>
              </div>
              <div class="conviction-bar">
                <div class="conviction-fill" :style="{ width: sessionStore.convictionScore * 100 + '%', background: convictionColor }"></div>
                <div class="conviction-threshold" :style="{ left: '90%' }">
                  <span class="threshold-label">Clear</span>
                </div>
              </div>
              <p class="conviction-hint">
                {{ sessionStore.decisionComplete ? 'Decision concluded' : 'The agent will conclude once your reasoning is clear enough or the loop hits its cap.' }}
              </p>
            </div>
            <div v-if="sessionStore.intentProfile.ambiguities.length > 0" class="ambiguities">
              <span class="label">Still unresolved</span>
              <div v-for="(a, i) in sessionStore.intentProfile.ambiguities" :key="i" class="ambiguity-item badge badge-warning">
                {{ a }}
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Intent Profile view (during conversation) -->
      <template v-else-if="sessionStore.intentProfile">
        <div class="profile-panel">
          <div class="profile-header">
            <h3>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
              Intent Profile
            </h3>
            <span class="badge badge-primary">Building...</span>
          </div>

          <div class="profile-content">
            <div v-if="sessionStore.intentProfile.primary_use_case" class="profile-item">
              <span class="label">Use Case</span>
              <span class="value">{{ sessionStore.intentProfile.primary_use_case }}</span>
            </div>
            <div v-if="sessionStore.intentProfile.product_category" class="profile-item">
              <span class="label">Category</span>
              <span class="value">{{ sessionStore.intentProfile.product_category }}</span>
            </div>
            <div v-if="sessionStore.intentProfile.constraints.budget_max" class="profile-item">
              <span class="label">Budget</span>
              <span class="value">₹{{ Number(sessionStore.intentProfile.constraints.budget_max).toLocaleString('en-IN') }}</span>
            </div>
            <div v-if="sessionStore.intentProfile.confidence_score" class="profile-item">
              <span class="label">Confidence</span>
              <div class="progress-bar" style="flex:1"><div class="fill" :style="{ width: sessionStore.intentProfile.confidence_score * 100 + '%' }"></div></div>
            </div>

            <!-- Conviction meter -->
            <div class="conviction-meter">
              <div class="conviction-label">
                <span>Conviction</span>
                <span class="conviction-value" :style="{ color: convictionColor }">
                  {{ Math.round(sessionStore.convictionScore * 100) }}%
                </span>
              </div>
              <div class="conviction-bar">
                <div class="conviction-fill" :style="{ width: sessionStore.convictionScore * 100 + '%', background: convictionColor }"></div>
                <div class="conviction-threshold" :style="{ left: '80%' }">
                  <span class="threshold-label">Ready</span>
                </div>
              </div>
              <p class="conviction-hint">
                {{ sessionStore.convictionScore >= 0.8 ? 'Ready for recommendations' : 'Keep chatting to build conviction' }}
              </p>
            </div>

            <!-- Ambiguities -->
            <div v-if="sessionStore.intentProfile.ambiguities.length > 0" class="ambiguities">
              <span class="label">Needs Clarification</span>
              <div v-for="(a, i) in sessionStore.intentProfile.ambiguities" :key="i" class="ambiguity-item badge badge-warning">
                {{ a }}
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Empty state -->
      <template v-else>
        <div class="empty-side">
          <div class="empty-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
          </div>
          <p>Start chatting to build your intent profile</p>
          <p class="hint">Your profile, conviction score, and product matches will appear here</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, watch, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import SwipeDeck from '@/components/products/SwipeDeck.vue'

const route = useRoute()
const sessionStore = useSessionStore()

const messagesContainer = ref<HTMLElement | null>(null)
const isMobile = ref(false)
const showMobilePanel = ref(false)
const isProductsHidden = ref(false)
const initialStatementDraft = ref('')

// Reset hidden state when new products arrive
watch(
  () => sessionStore.hasProducts,
  (has) => {
    if (has) isProductsHidden.value = false
  }
)

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  
  const id = route.params.id as string
  if (id && id !== sessionStore.sessionId) {
    await sessionStore.fetchSession(id)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

function checkMobile() {
  isMobile.value = window.innerWidth <= 860
  if (!isMobile.value) {
    showMobilePanel.value = false
  }
}

const inputPlaceholder = computed(() => {
  if (showDecisionOnboarding.value) return 'Start by writing your decision above...'
  if (sessionStore.isLoading) return 'Processing...'
  if (sessionStore.isDecisionMode && sessionStore.decisionComplete) return 'Decision complete. Start a new session for another case.'
  if (sessionStore.isDecisionMode) return 'Defend your reasoning...'
  if (sessionStore.phase === 'socratic_friction') return 'Answer to continue...'
  if (sessionStore.hasProducts) return 'Ask about the recommendations...'
  return 'Describe what you want to achieve...'
})

const showDecisionOnboarding = computed(() => {
  return sessionStore.isDecisionMode && !sessionStore.initialStatement
})

const isInputDisabled = computed(() => {
  if (sessionStore.isLoading) return true
  if (showDecisionOnboarding.value) return true
  if (sessionStore.isDecisionMode && sessionStore.decisionComplete) return true
  return false
})

const progressLabel = computed(() => {
  if (sessionStore.convictionScore >= 0.7) return 'Searching products and building recommendations...'
  return 'Understanding your needs...'
})

const convictionColor = computed(() => {
  const s = sessionStore.convictionScore
  if (s >= 0.8) return '#10b981'
  if (s >= 0.5) return '#f59e0b'
  return '#ef4444'
})

const decisionProgressLabel = computed(() => {
  if (sessionStore.decisionComplete) return 'Verdict ready'
  return `Turn ${Math.max(sessionStore.decisionTurn, 0)} of ${sessionStore.decisionMaxTurns}`
})

const decisionProgressWidth = computed(() => {
  if (!sessionStore.decisionMaxTurns) return '0%'
  return `${Math.min(100, (sessionStore.decisionTurn / sessionStore.decisionMaxTurns) * 100)}%`
})

const decisionStageCopy = computed(() => {
  const stageMap: Record<string, string> = {
    opening: 'Start from the real decision, not the marketing label.',
    clarify: 'Tighten what matters and cut away vague preferences.',
    challenge: 'Question whether the feature lust is actually justified.',
    tradeoff: 'Name what you are willing to lose to get what you want.',
    suggest: 'Test a sharper framing before committing money.',
    conclusion: 'The loop has enough signal to make the call.',
  }
  return stageMap[sessionStore.decisionStage] || 'Build enough clarity to make a higher-conviction choice.'
})

const decisionStatusLabel = computed(() => {
  if (sessionStore.decisionOutcome) return sessionStore.decisionOutcome.verdict
  return 'In progress'
})

const decisionVerdictBadgeClass = computed(() => {
  const verdict = sessionStore.decisionOutcome?.verdict
  if (verdict === 'Strong Yes') return 'badge-success'
  if (verdict === 'Weak Yes') return 'badge-primary'
  return 'badge-warning'
})

const mobilePanelLabel = computed(() => {
  if (showMobilePanel.value) return 'Back to Chat'
  if (sessionStore.isDecisionMode) return 'View Decision'
  return sessionStore.phase === 'product_recommendation' ? 'View Matches' : 'View Profile'
})

function handleSend(message: string) {
  if (isInputDisabled.value) return
  sessionStore.sendMessage(message)
}

async function handleInitialStatement() {
  const statement = initialStatementDraft.value.trim()
  if (!statement) return
  await sessionStore.submitInitialStatement(statement)
  initialStatementDraft.value = ''
}

function handleWidgetSubmit(value: string) {
  sessionStore.sendMessage(value)
}

function handleProductSwipe(productId: string, direction: string, reason?: string) {
  sessionStore.handleSwipe(productId, direction, reason)
}

// Auto-scroll to bottom
watch(
  () => sessionStore.messages.length,
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  }
)

// Also scroll when loading state changes
watch(
  () => sessionStore.isLoading,
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  }
)
</script>

<style scoped>
.session-view {
  height: 100%;
  display: flex;
  overflow: hidden;
}

/* Chat panel */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-right: 1px solid var(--border-color);
  position: relative;
}

.decision-mode-strip {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(209, 255, 115, 0.12);
  background:
    radial-gradient(circle at top left, rgba(209, 255, 115, 0.08), transparent 35%),
    linear-gradient(180deg, rgba(18, 22, 14, 0.95), rgba(10, 10, 10, 0.98));
}

.decision-mode-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #d1ff73;
  margin-bottom: 4px;
}

.decision-mode-strip h2 {
  font-size: 22px;
  line-height: 1.1;
}

.decision-progress-chip {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(209, 255, 115, 0.18);
  color: #d7f8a0;
  font-size: 12px;
  white-space: nowrap;
}

.decision-progress-chip.complete {
  background: rgba(209, 255, 115, 0.12);
}

.decision-onboarding {
  position: absolute;
  inset: 0;
  z-index: 35;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(5, 5, 5, 0.82);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.decision-onboarding-card {
  width: min(720px, 100%);
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background:
    radial-gradient(circle at top right, rgba(209, 255, 115, 0.1), transparent 30%),
    var(--bg-card);
}

.decision-kicker {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #d1ff73;
}

.decision-onboarding-copy h3 {
  font-size: 32px;
  line-height: 1.05;
  margin: 8px 0 10px;
}

.decision-onboarding-copy p {
  color: var(--text-secondary);
  max-width: 52ch;
}

.decision-onboarding-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.decision-textarea {
  width: 100%;
  resize: vertical;
  min-height: 140px;
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid rgba(209, 255, 115, 0.16);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-primary);
  font: inherit;
  outline: none;
}

.decision-textarea:focus {
  border-color: #d1ff73;
  box-shadow: 0 0 0 3px rgba(209, 255, 115, 0.08);
}

.decision-submit {
  align-self: flex-start;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Loading / Progress */
.typing-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}
.typing-avatar {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--bg-primary);
}
.typing-dots {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  background: transparent;
  border-radius: 16px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: typing-dot 1.2s infinite;
}

/* Products Overlay (replaces inline deck) */
.products-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(5, 5, 5, 0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  z-index: 30;
  display: flex;
  flex-direction: column;
}

.products-overlay-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 32px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.overlay-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
  font-family: 'Outfit', sans-serif;
  letter-spacing: -0.5px;
  color: var(--text-primary);
}

.products-overlay-content {
  flex: 1;
  overflow: hidden;
  padding: 20px;
  display: flex;
  align-items: stretch;
  justify-content: center;
}

/* Ensure SwipeDeck inside overlay takes max space */
.products-overlay-content :deep(.swipe-deck) {
  width: 100%;
  max-width: 600px;
}

.reshow-products-bar {
  position: absolute;
  bottom: 100px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  z-index: 20;
  pointer-events: none;
}

.reshow-products-bar .btn {
  pointer-events: auto;
  box-shadow: 0 10px 40px -10px rgba(0,0,0,1);
  background: var(--text-primary);
  color: var(--bg-primary);
}

.close-overlay-btn {
  border: 1px solid var(--border-color);
}
.close-overlay-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* Search progress */
.search-progress {
  margin-left: 42px;
  max-width: 320px;
}
.search-progress-steps {
  margin-bottom: 6px;
}
.step {
  display: flex;
  align-items: center;
  gap: 8px;
}
.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-primary);
  animation: pulse-dot 1s infinite alternate;
}
.step-text {
  font-size: 12px;
  color: var(--text-secondary);
}
.search-progress-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
  overflow: hidden;
}
.search-progress-fill {
  height: 100%;
  background: var(--text-primary);
  width: 0%;
  animation: progress-fill 8s cubic-bezier(0.1, 0.7, 0.1, 1) forwards;
}
@keyframes progress-fill {
  0% { width: 0%; }
  20% { width: 15%; }
  40% { width: 35%; }
  60% { width: 55%; }
  80% { width: 75%; }
  100% { width: 95%; }
}
@keyframes pulse-dot {
  0% { opacity: 0.4; transform: scale(0.8); }
  100% { opacity: 1; transform: scale(1.2); }
}

/* Side panel */
.side-panel {
  width: 440px;
  flex-shrink: 0;
  overflow-y: auto;
  background: var(--bg-secondary);
}

/* Profile panel */
.profile-panel {
  padding: 20px;
}

.decision-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.decision-rail {
  padding: 16px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(209, 255, 115, 0.14);
  background: rgba(209, 255, 115, 0.04);
}

.decision-rail-top {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.decision-stage-copy {
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.decision-outcome-card {
  padding: 18px;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
  border: 1px solid var(--border-color);
}

.decision-outcome-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.decision-verdict {
  font-family: 'Outfit', sans-serif;
  font-size: 28px;
  line-height: 1;
}

.decision-outcome-text {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 14px;
}

.decision-action-block {
  margin-bottom: 14px;
}

.decision-action-block p {
  font-size: 14px;
}

.decision-tradeoffs {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.profile-item-stack {
  align-items: flex-start;
}

.decision-statement {
  text-transform: none;
  line-height: 1.5;
}
.profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.profile-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
}
.profile-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.profile-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.profile-item .label {
  font-size: 12px;
  color: var(--text-muted);
  width: 80px;
  flex-shrink: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.profile-item .value {
  font-size: 14px;
  font-weight: 500;
  text-transform: capitalize;
}

/* Conviction meter */
.conviction-meter {
  padding: 16px;
  background: var(--bg-glass);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  margin-top: 8px;
}
.conviction-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}
.conviction-value {
  font-weight: 700;
  font-family: 'Outfit', sans-serif;
  font-size: 18px;
}
.conviction-bar {
  position: relative;
  height: 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
  margin-bottom: 8px;
}
.conviction-fill {
  height: 100%;
  border-radius: 4px;
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.conviction-threshold {
  position: absolute;
  top: -4px;
  bottom: -4px;
  width: 2px;
  background: var(--text-muted);
}
.threshold-label {
  position: absolute;
  bottom: -18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 9px;
  color: var(--text-muted);
  white-space: nowrap;
}
.conviction-hint {
  font-size: 12px;
  color: var(--text-muted);
}

/* Ambiguities */
.ambiguities {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ambiguities .label {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}
.ambiguity-item {
  font-size: 12px;
}

/* Empty state */
.empty-side {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
  font-size: 14px;
}
.empty-icon {
  margin-bottom: 16px;
}
.hint {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 8px;
}

/* Mobile Toggle Button */
.mobile-toggle-bar {
  padding: 8px 16px;
  display: flex;
  justify-content: center;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.mobile-toggle-bar .btn {
  width: 100%;
  font-size: 13px;
}

/* Responsive */
@media (max-width: 860px) {
  .session-view {
    position: relative;
    flex-direction: row;
  }
  .chat-panel {
    width: 100%;
    height: 100%;
    flex: 1;
    border-right: none;
  }
  .side-panel {
    position: absolute;
    top: 0;
    bottom: 0;
    right: -100%;
    width: 100%;
    max-width: none;
    max-height: none;
    background: var(--bg-primary);
    z-index: 40;
    transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: -10px 0 30px rgba(0,0,0,0.5);
    border-left: 1px solid var(--border-color);
  }
  .side-panel.mobile-open {
    right: 0;
  }

  .decision-mode-strip {
    flex-direction: column;
    align-items: flex-start;
  }

  .decision-onboarding {
    padding: 16px;
  }

  .decision-onboarding-card {
    padding: 22px;
  }

  .decision-onboarding-copy h3 {
    font-size: 26px;
  }
}
</style>
