<template>
  <div class="chat-input">
    <!-- 快捷指令 -->
    <div class="quick-actions">
      <el-tag
        v-for="q in quickList"
        :key="q.label"
        :type="q.type as any"
        class="quick-tag"
        @click="emit('send', q.text)"
      >
        {{ q.label }}
      </el-tag>
    </div>

    <!-- 输入行 -->
    <div class="input-row">
      <el-input
        ref="inputRef"
        v-model="text"
        type="textarea"
        :rows="3"
        :disabled="disabled"
        resize="none"
        placeholder="输入运维指令，Enter 发送，Shift+Enter 换行"
        @keydown.enter="onEnter"
      />
      <el-button
        type="primary"
        :disabled="disabled || !text.trim()"
        :loading="disabled"
        @click="send"
      >
        {{ disabled ? '回复中...' : '发送' }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'

defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ send: [text: string] }>()

const text = ref('')
const inputRef = ref<InstanceType<typeof import('element-plus').ElInput>>()

const quickList = [
  { label: '🔍 系统状态', text: '帮我看看当前系统状态', type: 'info' },
  { label: '🧹 磁盘清理', text: '帮我检查磁盘空间使用情况', type: 'warning' },
  { label: '📋 进程检查', text: '帮我查看占用最高的进程', type: 'primary' },
]

function onEnter(e: KeyboardEvent) {
  if (e.shiftKey) return         // Shift+Enter 换行
  e.preventDefault()
  send()
}

function send() {
  const msg = text.value.trim()
  if (!msg) return
  emit('send', msg)
  text.value = ''
  nextTick(() => inputRef.value?.focus())
}

onMounted(() => {
  nextTick(() => inputRef.value?.focus())
})
</script>

<style scoped>
.chat-input {
  padding: 12px 16px;
  background: var(--bg-panel);
  border-top: 1px solid var(--border-color);
}

.quick-actions {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}

.quick-tag {
  cursor: pointer;
  user-select: none;
}
.quick-tag:hover {
  opacity: 0.85;
}

.input-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.input-row :deep(.el-textarea__inner) {
  background: var(--bg-dark);
  color: var(--text-primary);
  border-color: var(--border-color);
}
</style>
