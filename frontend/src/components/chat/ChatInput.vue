<template>
  <form class="chat-input-wrapper" @submit.prevent="handleSubmit">
    <input
      ref="inputRef"
      class="input chat-input"
      :placeholder="placeholder"
      v-model="text"
      :disabled="disabled"
      @keydown.enter.exact="handleSubmit"
    />
    <button
      type="submit"
      class="send-btn"
      :disabled="disabled || !text.trim()"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="22" y1="2" x2="11" y2="13" />
        <polygon points="22 2 15 22 11 13 2 9 22 2" />
      </svg>
    </button>
  </form>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{
  disabled?: boolean
  placeholder?: string
}>()

const emit = defineEmits<{
  send: [message: string]
}>()

const text = ref('')
const inputRef = ref<HTMLInputElement>()

function handleSubmit() {
  const msg = text.value.trim()
  if (!msg || props.disabled) return
  emit('send', msg)
  text.value = ''
}

onMounted(() => {
  inputRef.value?.focus()
})
</script>

<style scoped>
.chat-input-wrapper {
  display: flex;
  gap: 8px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}
.chat-input {
  flex: 1;
  padding: 14px 18px;
  font-size: 15px;
  border-radius: 14px;
}
.send-btn {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--accent-gradient);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}
.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 20px var(--accent-glow);
}
.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
