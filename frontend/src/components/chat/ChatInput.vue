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
  gap: 12px;
  padding: 12px;
  background: rgba(15, 15, 15, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-color);
  border-radius: 24px;
  margin: 0 20px 20px 20px;
  box-shadow: 0 10px 40px -10px rgba(0,0,0,0.8);
}
.chat-input {
  flex: 1;
  padding: 12px 16px;
  font-size: 15px;
  background: transparent;
  border: none;
  border-radius: 12px;
}
.chat-input:focus {
  box-shadow: none;
}
.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--text-primary);
  border: none;
  color: var(--bg-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  flex-shrink: 0;
}
.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  background: #FFFFFF;
  box-shadow: 0 4px 20px rgba(255, 255, 255, 0.15);
}
.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
