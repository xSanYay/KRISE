<template>
  <div class="swipe-deck" v-if="products.length > 0">
    <div class="deck-header">
      <h3 class="deck-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v3"/></svg>
        Product Recommendations
      </h3>
      <span class="deck-count badge badge-primary">{{ products.length }} left</span>
    </div>

    <div class="deck-container">
      <!-- Show top card -->
      <ProductCard
        v-if="currentProduct"
        :scored="currentProduct"
        @swipe="handleSwipe"
      />

      <div v-if="products.length === 0" class="deck-empty glass">
        <p>No more products — refine your search to see more!</p>
      </div>
    </div>

    <!-- Swipe reason modal -->
    <div v-if="showReasonPicker" class="reason-overlay" @click.self="cancelReason">
      <div class="reason-modal glass-lg animate-slide-up">
        <h4>Why not this product?</h4>
        <div class="reason-options">
          <button v-for="r in reasons" :key="r.value" class="reason-btn btn btn-ghost" @click="submitReason(r.value)">
            {{ r.emoji }} {{ r.label }}
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

const currentProduct = computed(() => props.products[0] || null)

const reasons = [
  { value: 'too_expensive', emoji: '💰', label: 'Too expensive' },
  { value: 'wrong_brand', emoji: '🏷️', label: 'Wrong brand' },
  { value: 'insufficient_specs', emoji: '⚙️', label: 'Insufficient specs' },
  { value: 'poor_reviews', emoji: '👎', label: 'Poor reviews' },
  { value: 'not_interested', emoji: '🤷', label: 'Just not interested' },
]

function handleSwipe(direction: string) {
  if (!currentProduct.value) return

  if (direction === 'left') {
    // Show reason picker for left swipes
    pendingSwipeId.value = currentProduct.value.product.id
    showReasonPicker.value = true
  } else {
    emit('swipe', currentProduct.value.product.id, direction)
  }
}

function submitReason(reason: string) {
  emit('swipe', pendingSwipeId.value, 'left', reason)
  showReasonPicker.value = false
}

function cancelReason() {
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

.deck-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}
.deck-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}

.deck-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  overflow-y: auto;
}

.deck-empty {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
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
}
.reason-btn:hover {
  background: rgba(124, 58, 237, 0.1);
  border-color: var(--accent-primary);
}

.shortlist-indicator {
  position: absolute;
  bottom: 12px;
  right: 12px;
  font-size: 12px;
}
</style>
