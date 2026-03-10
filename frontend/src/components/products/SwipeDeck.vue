<template>
  <div class="swipe-deck" v-if="products.length > 0">
    <div class="deck-counter">{{ products.length }} LEFT</div>
    <div class="deck-container">
      <!-- Transition wrapper for smooth card change -->
      <Transition name="card-swap" mode="out-in">
        <ProductCard
          v-if="currentProduct"
          :key="currentProduct.product.id"
          :scored="currentProduct"
          @swipe="handleSwipe"
        />
      </Transition>
    </div>

    <!-- Swipe reason modal -->
    <div v-if="showReasonPicker" class="reason-overlay" @click.self="cancelReason">
      <div class="reason-modal glass-lg animate-slide-up">
        <h4>Why not this product?</h4>
        <div class="reason-options">
          <button v-for="r in reasons" :key="r.value" class="reason-btn btn btn-ghost" @click="submitReason(r.value)">
            {{ r.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Shortlist -->
    <div v-if="shortlistCount > 0" class="shortlist-indicator badge badge-success">
      ✓ {{ shortlistCount }} in shortlist
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import ProductCard from './ProductCard.vue'
import type { ProductScore } from '@/lib/api'

const props = defineProps<{
  products: ProductScore[]
  shortlistCount: number
}>()

const emit = defineEmits<{
  swipe: [productId: string, direction: string, reason?: string]
}>()

const showReasonPicker = ref(false)
const pendingSwipeId = ref('')
const reasonPromptCount = ref(0) // Track how many times reason modal has been shown

const currentProduct = computed(() => props.products[0] || null)

const reasons = [
  { value: 'too_expensive', label: 'Too expensive' },
  { value: 'wrong_brand', label: 'Wrong brand' },
  { value: 'insufficient_specs', label: 'Insufficient specs' },
  { value: 'poor_reviews', label: 'Poor reviews' },
  { value: 'not_interested', label: 'Just not interested' },
]

function handleSwipe(direction: string) {
  if (!currentProduct.value) return

  if (direction === 'left') {
    if (reasonPromptCount.value < 4) {
      // Show reason picker for left swipes (up to 4 times)
      pendingSwipeId.value = currentProduct.value.product.id
      showReasonPicker.value = true
    } else {
      // Auto-skip reason after asking enough times
      emit('swipe', currentProduct.value.product.id, 'left', 'not_interested')
    }
  } else {
    emit('swipe', currentProduct.value.product.id, direction)
  }
}

function submitReason(reason: string) {
  emit('swipe', pendingSwipeId.value, 'left', reason)
  reasonPromptCount.value++
  showReasonPicker.value = false
}

function cancelReason() {
  emit('swipe', pendingSwipeId.value, 'left', 'not_interested')
  reasonPromptCount.value++
  showReasonPicker.value = false
}
</script>

<style scoped>
.swipe-deck {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.deck-counter {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  text-align: center;
  padding: 8px 0 4px;
  flex-shrink: 0;
}

.deck-container {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 8px 16px 16px;
  overflow-y: auto;
  overflow-x: hidden;
}

.deck-empty {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-lg);
  margin: 20px;
  width: 100%;
}

/* Reason picker overlay */
.reason-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(4px);
}
.reason-modal {
  padding: 24px;
  max-width: 340px;
  width: 90%;
}
.reason-modal h4 {
  font-size: 16px;
  margin-bottom: 16px;
  text-align: center;
}
.reason-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.reason-btn {
  justify-content: flex-start;
  padding: 12px 16px;
  font-size: 14px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
}
.reason-btn:hover {
  background: var(--text-primary);
  color: var(--bg-primary);
  border-color: var(--text-primary);
}

.shortlist-indicator {
  position: absolute;
  bottom: 12px;
  right: 12px;
  font-size: 12px;
}

/* Card swap transition */
.card-swap-enter-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.card-swap-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.card-swap-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.97);
}
.card-swap-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.97);
}
</style>
