<template>
  <div class="chat-msg" :class="[`msg-${msg.role}`, { 'animate-fade-in': true }]">
    <div class="msg-avatar" v-if="msg.role === 'agent'">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
      </svg>
    </div>
    <div class="msg-bubble">
      <div class="msg-content" v-html="formatContent(msg.content)"></div>

      <!-- Interactive Widgets -->
      <div v-if="msg.widget && !widgetUsed" class="widget-container">

        <!-- Budget Slider with Manual Input -->
        <div v-if="msg.widget.widget_type === 'budget_slider'" class="widget budget-widget">
          <label class="widget-label">{{ msg.widget.label }}</label>
          <div class="slider-row">
            <span class="slider-min">₹{{ formatNum(msg.widget.min_value || 5000) }}</span>
            <input
              type="range"
              :min="msg.widget.min_value || 5000"
              :max="msg.widget.max_value || 200000"
              :step="msg.widget.step || 1000"
              v-model.number="sliderValue"
              class="budget-slider"
            />
            <span class="slider-max">₹{{ formatNum(msg.widget.max_value || 200000) }}</span>
          </div>
          <div class="budget-input-row">
            <span class="budget-currency">₹</span>
            <input
              type="number"
              v-model.number="sliderValue"
              :min="msg.widget.min_value || 5000"
              :max="msg.widget.max_value || 200000"
              :step="msg.widget.step || 1000"
              class="budget-text-input"
              @focus="($event.target as HTMLInputElement).select()"
              @keydown.enter="submitWidget(`My budget is ₹${sliderValue}`)"
            />
          </div>
          <button class="btn btn-primary btn-sm" @click="submitWidget(`My budget is ₹${sliderValue}`)">
            Set Budget
          </button>
        </div>

        <!-- Category Picker (single select) -->
        <div v-if="msg.widget.widget_type === 'category_picker'" class="widget category-widget">
          <label class="widget-label">{{ msg.widget.label }}</label>
          <div class="chip-grid">
            <button
              v-for="opt in msg.widget.options"
              :key="opt"
              class="chip-btn"
              @click="submitWidget(opt)"
            >
              {{ opt }}
            </button>
          </div>
        </div>

        <!-- Brand Picker (multi-select) -->
        <div v-if="msg.widget.widget_type === 'brand_picker'" class="widget brand-widget">
          <label class="widget-label">{{ msg.widget.label }}</label>
          <div class="chip-grid">
            <button
              v-for="opt in msg.widget.options"
              :key="opt"
              class="chip-btn"
              :class="{ 'chip-selected': selectedBrands.includes(opt) }"
              @click="toggleBrand(opt)"
            >
              {{ opt }}
              <svg v-if="selectedBrands.includes(opt)" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </button>
          </div>
          <button
            v-if="selectedBrands.length > 0"
            class="btn btn-primary btn-sm"
            style="margin-top: 10px"
            @click="submitBrands"
          >
            Confirm {{ selectedBrands.length }} brand{{ selectedBrands.length > 1 ? 's' : '' }}
          </button>
        </div>
      </div>

      <!-- Widget used confirmation -->
      <div v-if="widgetUsed" class="widget-done">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span>Submitted</span>
      </div>

      <div class="msg-meta">
        <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
        <span v-if="msg.role === 'agent' && msg.type === 'question'" class="badge badge-primary" style="font-size:10px">
          Clarification
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { ChatMessage } from '@/stores/session'

const props = defineProps<{ msg: ChatMessage }>()
const emit = defineEmits<{
  widgetSubmit: [value: string]
}>()

const sliderValue = ref(
  props.msg.widget
    ? Math.round(((props.msg.widget.min_value ?? 5000) + (props.msg.widget.max_value ?? 200000)) / 2 / 1000) * 1000
    : 20000
)
const widgetUsed = ref(false)
const selectedBrands = ref<string[]>([])

function formatContent(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br />')
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatNum(n: number): string {
  return Number(n).toLocaleString('en-IN')
}

function toggleBrand(brand: string) {
  if (brand === 'No preference') {
    selectedBrands.value = ['No preference']
    return
  }
  // Remove "No preference" if selecting a real brand
  selectedBrands.value = selectedBrands.value.filter(b => b !== 'No preference')

  const idx = selectedBrands.value.indexOf(brand)
  if (idx >= 0) {
    selectedBrands.value.splice(idx, 1)
  } else {
    selectedBrands.value.push(brand)
  }
}

function submitBrands() {
  if (selectedBrands.value.includes('No preference')) {
    submitWidget('No brand preference')
  } else {
    submitWidget(`I prefer ${selectedBrands.value.join(', ')}`)
  }
}

function submitWidget(value: string) {
  widgetUsed.value = true
  emit('widgetSubmit', value)
}
</script>

<style scoped>
.chat-msg {
  display: flex;
  gap: 10px;
  padding: 4px 0;
  max-width: 85%;
}
.msg-user {
  margin-left: auto;
  flex-direction: row-reverse;
}
.msg-agent, .msg-system {
  margin-right: auto;
}
.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: var(--accent-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: white;
}
.msg-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  max-width: 100%;
}
.msg-user .msg-bubble {
  background: rgba(124, 58, 237, 0.15);
  border: 1px solid rgba(124, 58, 237, 0.25);
  border-bottom-right-radius: 4px;
}
.msg-agent .msg-bubble {
  background: var(--bg-glass);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 4px;
}
.msg-system .msg-bubble {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  font-size: 13px;
}
.msg-content {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}
.msg-content :deep(strong) {
  color: var(--text-primary);
  font-weight: 600;
}
.msg-content :deep(em) {
  color: var(--accent-secondary);
}
.msg-content :deep(code) {
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 13px;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.msg-time {
  font-size: 11px;
  color: var(--text-muted);
}

/* Widget styles */
.widget-container {
  margin-top: 12px;
}
.widget {
  padding: 14px;
  border-radius: 12px;
  background: rgba(124, 58, 237, 0.06);
  border: 1px solid rgba(124, 58, 237, 0.15);
}
.widget-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.widget-done {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
  color: #10b981;
}

/* Budget Slider */
.slider-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.slider-min, .slider-max {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}
.budget-slider {
  flex: 1;
  -webkit-appearance: none;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}
.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--accent-primary);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}
.budget-input-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 10px;
}
.budget-currency {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-secondary);
}
.budget-text-input {
  flex: 1;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 700;
  font-family: 'Outfit', sans-serif;
  outline: none;
}
.budget-text-input:focus {
  border-color: var(--accent-primary);
}
/* Hide number spinner arrows */
.budget-text-input::-webkit-outer-spin-button,
.budget-text-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.budget-text-input[type=number] {
  -moz-appearance: textfield;
}
.btn-sm {
  padding: 6px 16px;
  font-size: 13px;
  width: 100%;
}

/* Category / Brand Picker */
.chip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.chip-btn:hover {
  background: rgba(124, 58, 237, 0.15);
  border-color: var(--accent-primary);
}
.chip-selected {
  background: rgba(124, 58, 237, 0.25) !important;
  border-color: var(--accent-primary) !important;
  color: white;
}
</style>
