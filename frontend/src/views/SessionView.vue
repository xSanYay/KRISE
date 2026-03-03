<template>
  <div class="session-view">
    <!-- Left panel: Chat -->
    <div class="chat-panel">
      <div class="chat-messages" ref="messagesContainer">
        <ChatMessage
          v-for="(msg, i) in sessionStore.messages"
          :key="i"
          :msg="msg"
        />

        <!-- Typing indicator -->
        <div v-if="sessionStore.isLoading" class="typing-indicator animate-fade-in">
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
      </div>

      <ChatInput
        :disabled="sessionStore.isLoading"
        :placeholder="inputPlaceholder"
        @send="handleSend"
      />
    </div>

    <!-- Right panel: Products or Intent Profile -->
    <div class="side-panel">
      <!-- Products view -->
      <template v-if="sessionStore.hasProducts">
        <SwipeDeck
          :products="sessionStore.products"
          :shortlist-count="sessionStore.shortlist.length"
          @swipe="handleProductSwipe"
        />
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
                {{ sessionStore.convictionScore >= 0.8 ? '✅ Ready for recommendations!' : '💬 Keep chatting to build conviction' }}
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
import { computed, nextTick, watch, ref } from 'vue'
import { useSessionStore } from '@/stores/session'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import SwipeDeck from '@/components/products/SwipeDeck.vue'

const sessionStore = useSessionStore()
const messagesContainer = ref<HTMLElement>()

const inputPlaceholder = computed(() => {
  if (sessionStore.isLoading) return 'Krise is thinking...'
  if (sessionStore.phase === 'socratic_friction') return 'Answer the question to build conviction...'
  if (sessionStore.hasProducts) return 'Ask about the recommendations...'
  return 'Describe what you want to achieve...'
})

const convictionColor = computed(() => {
  const s = sessionStore.convictionScore
  if (s >= 0.8) return '#10b981'
  if (s >= 0.5) return '#f59e0b'
  return '#ef4444'
})

function handleSend(message: string) {
  sessionStore.sendMessage(message)
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
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Typing indicator */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
}
.typing-avatar {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: var(--accent-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}
.typing-dots {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: var(--bg-glass);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  border-bottom-left-radius: 4px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: typing-dot 1.2s infinite;
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

/* Responsive */
@media (max-width: 860px) {
  .session-view {
    flex-direction: column;
  }
  .side-panel {
    width: 100%;
    max-height: 45vh;
    border-right: none;
    border-top: 1px solid var(--border-color);
  }
}
</style>
