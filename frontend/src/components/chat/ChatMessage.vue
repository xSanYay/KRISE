<template>
  <div class="chat-msg" :class="[`msg-${msg.role}`, { 'animate-fade-in': true }]">
    <div class="msg-avatar" v-if="msg.role === 'agent'">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
      </svg>
    </div>
    <div class="msg-bubble">
      <div class="msg-content" v-html="formatContent(msg.content)"></div>
      <div class="msg-meta">
        <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
        <span v-if="msg.role === 'agent' && msg.type === 'question'" class="badge badge-primary" style="font-size:10px">
          Socratic Question
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from '@/stores/session'

defineProps<{ msg: ChatMessage }>()

function formatContent(text: string): string {
  // Simple markdown: bold, italics
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br />')
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
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
</style>
