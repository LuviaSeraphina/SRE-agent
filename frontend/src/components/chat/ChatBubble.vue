<template>
  <div
    class="bubble-wrapper"
    :class="[message.role, { streaming }]"
  >
    <!-- 头像 + 时间 -->
    <div class="bubble-meta">
      <span class="avatar">{{ avatar }}</span>
      <span class="time">{{ timeStr }}</span>
    </div>

    <!-- 消息内容 -->
    <div class="bubble-body">
      <!-- Markdown 渲染 -->
      <div class="content markdown-body" v-html="renderedContent" />

      <!-- 闪烁光标（流式输出中） -->
      <span v-if="isStreaming" class="cursor-blink" />

      <!-- 工具调用卡片列表 -->
      <div v-if="message.tool_calls?.length" class="tool-calls">
        <ToolCallCard
          v-for="tc in message.tool_calls"
          :key="tc.id"
          :tool-call="tc"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/types'
import { renderMarkdown } from '@/utils/markdown'
import ToolCallCard from './ToolCallCard.vue'

const props = defineProps<{
  message: ChatMessage
  streaming: boolean
}>()

const isStreaming = computed(() => props.streaming && props.message.role === 'assistant')

const avatar = computed(() => {
  switch (props.message.role) {
    case 'user':      return '👤'
    case 'assistant': return '🤖'
    case 'system':    return '⚙️'
    case 'tool':      return '🔧'
    default:          return '💬'
  }
})

const timeStr = computed(() => {
  const d = new Date(props.message.timestamp)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  return renderMarkdown(props.message.content)
})
</script>

<style scoped>
.bubble-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 75%;
  margin-bottom: 16px;
  animation: fadeInUp 0.3s ease;
}

/* ---- 用户消息：右对齐 ---- */
.bubble-wrapper.user {
  margin-left: auto;
  align-items: flex-end;
}
.bubble-wrapper.user .bubble-meta {
  flex-direction: row-reverse;
}
.bubble-wrapper.user .bubble-body {
  background: var(--color-primary);
  color: #fff;
  border-radius: 12px 4px 12px 12px;
}

/* ---- Agent 消息：左对齐 ---- */
.bubble-wrapper.assistant {
  margin-right: auto;
  align-items: flex-start;
}
.bubble-wrapper.assistant .bubble-body {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-radius: 4px 12px 12px 12px;
}

/* ---- 系统/工具消息 ---- */
.bubble-wrapper.system .bubble-body,
.bubble-wrapper.tool .bubble-body {
  background: var(--bg-panel);
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  font-size: 12px;
  opacity: 0.85;
}

/* ---- 元信息 ---- */
.bubble-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.avatar {
  font-size: 16px;
}
.time {
  font-size: 11px;
  color: var(--text-secondary);
}

/* ---- 消息体 ---- */
.bubble-body {
  padding: 10px 14px;
  line-height: 1.6;
  word-break: break-word;
}

/* ---- Markdown 内容 ---- */
.content :deep(p) { margin: 4px 0; }
.content :deep(ul), .content :deep(ol) { padding-left: 18px; margin: 4px 0; }
.content :deep(table) { border-collapse: collapse; margin: 6px 0; }
.content :deep(th), .content :deep(td) {
  border: 1px solid var(--border-color);
  padding: 4px 8px;
  font-size: 13px;
}
.content :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: 10px;
  margin: 6px 0;
  opacity: 0.85;
}

/* ---- 工具调用 ---- */
.tool-calls {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ---- 闪烁光标 ---- */
.cursor-blink {
  display: inline-block;
  width: 2px;
  height: 16px;
  background: var(--color-primary);
  animation: blink 0.5s infinite;
  vertical-align: text-bottom;
}
</style>
