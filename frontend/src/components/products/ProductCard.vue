<template>
  <div class="product-card glass-lg animate-fade-in" :class="{ 'card-swiping': isSwiping }">
    <!-- Score badge -->
    <div class="score-badge">
      <span class="score-value">{{ Math.round(scored.total_score) }}</span>
      <span class="score-label">score</span>
    </div>

    <!-- Source badge -->
    <div class="source-badge badge" :class="sourceBadgeClass">
      {{ scored.product.source }}
    </div>

    <!-- Product image or placeholder -->
    <div class="card-image">
      <img
        v-if="scored.product.images.length > 0"
        :src="scored.product.images[0]"
        :alt="scored.product.title"
        loading="lazy"
      />
      <div v-else class="img-placeholder">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><path d="M21 15l-5-5L5 21" />
        </svg>
      </div>
    </div>

    <!-- Product info -->
    <div class="card-body">
      <h3 class="card-title">{{ scored.product.title }}</h3>

      <div class="card-price">
        <span class="price-current">₹{{ formatPrice(scored.product.price.current) }}</span>
        <span v-if="scored.product.price.original" class="price-original">
          ₹{{ formatPrice(scored.product.price.original) }}
        </span>
        <span v-if="scored.product.price.discount_percent" class="price-discount badge badge-success">
          {{ Math.round(scored.product.price.discount_percent) }}% off
        </span>
      </div>

      <!-- Rating -->
      <div v-if="scored.product.rating" class="card-rating">
        <div class="stars">
          <span v-for="i in 5" :key="i" class="star" :class="{ filled: i <= Math.round(scored.product.rating!) }">★</span>
        </div>
        <span class="rating-text">{{ scored.product.rating }}</span>
        <span v-if="scored.product.review_count" class="review-count">({{ formatCount(scored.product.review_count) }})</span>
      </div>

      <!-- Score breakdown -->
      <div class="score-bars">
        <div class="score-row">
          <span class="score-label-sm">Tech Match</span>
          <div class="progress-bar"><div class="fill" :style="{ width: scored.technical_match + '%' }"></div></div>
          <span class="score-num">{{ Math.round(scored.technical_match) }}</span>
        </div>
        <div class="score-row">
          <span class="score-label-sm">Sentiment</span>
          <div class="progress-bar"><div class="fill" :style="{ width: scored.sentiment_score + '%' }"></div></div>
          <span class="score-num">{{ Math.round(scored.sentiment_score) }}</span>
        </div>
        <div class="score-row">
          <span class="score-label-sm">Value</span>
          <div class="progress-bar"><div class="fill" :style="{ width: scored.value_for_money + '%' }"></div></div>
          <span class="score-num">{{ Math.round(scored.value_for_money) }}</span>
        </div>
      </div>

      <!-- Explanation -->
      <p v-if="scored.explanation" class="card-explanation">
        💡 {{ scored.explanation }}
      </p>

      <!-- Sentiment summary -->
      <div v-if="scored.product.sentiment.summary" class="sentiment-section">
        <div class="sentiment-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/></svg>
          Real User Sentiment
        </div>
        <p class="sentiment-text">{{ scored.product.sentiment.summary }}</p>
      </div>
    </div>

    <!-- Action buttons -->
    <div class="card-actions">
      <button class="action-btn reject" @click="$emit('swipe', 'left')" title="Not interested">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
      <button class="action-btn save" @click="$emit('swipe', 'up')" title="Save for later">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
      </button>
      <button class="action-btn accept" @click="$emit('swipe', 'right')" title="Add to shortlist">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ProductScore } from '@/lib/api'

const props = defineProps<{
  scored: ProductScore
  isSwiping?: boolean
}>()

defineEmits<{
  swipe: [direction: string]
}>()

const sourceBadgeClass = props.scored.product.source === 'amazon'
  ? 'badge-warning'
  : 'badge-primary'

function formatPrice(n: number): string {
  return n.toLocaleString('en-IN')
}

function formatCount(n: number): string {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}
</script>

<style scoped>
.product-card {
  position: relative;
  max-width: 400px;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.score-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 44px;
  height: 44px;
  border-radius: 4px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2;
  box-shadow: 0 4px 15px rgba(0,0,0,0.5);
}
.score-value {
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 16px;
  line-height: 1;
  color: white;
}
.score-label {
  font-size: 8px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 0.5px;
}

.source-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 2;
  text-transform: capitalize;
}

.card-image {
  height: 280px;
  background: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-bottom: 1px solid var(--border-color);
}
.card-image img {
  max-height: 100%;
  max-width: 100%;
  object-fit: cover;
}
.img-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-body {
  padding: 16px 20px;
  flex: 1;
  overflow-y: auto;
  max-height: 320px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-price {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.price-current {
  font-family: 'Outfit', sans-serif;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -1px;
}
.price-original {
  font-size: 14px;
  color: var(--text-muted);
  text-decoration: line-through;
}

.card-rating {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}
.star {
  color: var(--text-muted);
  font-size: 14px;
}
.star.filled {
  color: #fbbf24;
}
.rating-text {
  font-weight: 600;
  font-size: 13px;
}
.review-count {
  font-size: 12px;
  color: var(--text-muted);
}

.score-bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.score-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.score-label-sm {
  font-size: 11px;
  color: var(--text-muted);
  width: 70px;
  flex-shrink: 0;
}
.score-row .progress-bar {
  flex: 1;
  height: 2px;
  background: #333333;
}
.score-row .progress-bar .fill {
  background: var(--text-primary);
  height: 100%;
}
.score-num {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  width: 24px;
  text-align: right;
}

.card-explanation {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  padding: 12px 0;
  border-top: 1px dashed var(--border-color);
  margin-top: 12px;
  margin-bottom: 10px;
}

.sentiment-section {
  margin-top: 4px;
}
.sentiment-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
  font-weight: 500;
}
.sentiment-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* Action buttons */
.card-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding: 14px 20px;
  border-top: 1px solid var(--border-color);
}
.action-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 2px solid;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.action-btn.reject {
  border-color: var(--border-color);
  color: var(--text-primary);
}
.action-btn.reject:hover {
  background: #ef4444;
  border-color: #ef4444;
  color: white;
  transform: scale(1.05);
}
.action-btn.save {
  border-color: var(--border-color);
  color: var(--text-primary);
}
.action-btn.save:hover {
  background: #f59e0b;
  border-color: #f59e0b;
  color: white;
  transform: scale(1.05);
}
.action-btn.accept {
  border-color: var(--text-primary);
  color: var(--bg-primary);
  background: var(--text-primary);
}
.action-btn.accept:hover {
  background: #10b981;
  border-color: #10b981;
  color: white;
  transform: scale(1.05);
}
</style>
