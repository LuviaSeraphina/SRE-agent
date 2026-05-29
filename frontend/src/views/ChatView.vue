<template>
  <div class="chat-page">
    <!-- 欢迎引导 -->
    <div v-if="store.messages.length === 0" class="welcome">
      <div class="welcome-icon">🤖</div>
      <h2>你好，我是麒麟安全运维 Agent</h2>
      <p class="welcome-desc">通过自然语言对话，我可以帮你感知系统状态、排查故障、执行运维操作</p>
      <div class="welcome-actions">
        <el-card
          v-for="q in quickStarts"
          :key="q.label"
          shadow="hover"
          class="welcome-card"
          @click="store.sendMessage(q.text)"
        >
          <span class="card-icon">{{ q.icon }}</span>
          <span>{{ q.label }}</span>
        </el-card>
      </div>
    </div>

    <!-- 消息列表 -->
    <div v-else ref="listRef" class="message-list">
      <ChatBubble
        v-for="msg in store.messages"
        :key="msg.id"
        :message="msg"
        :streaming="store.streaming && msg.id === lastAgentId"
      />
    </div>

    <!-- 确认弹窗 -->
    <ConfirmDialog />

    <!-- 输入框 -->
    <ChatInput :disabled="store.streaming" @send="store.sendMessage" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import ConfirmDialog from '@/components/chat/ConfirmDialog.vue'

const store = useChatStore()
const listRef = ref<HTMLDivElement>()

const lastAgentId = computed(() => {
  const msgs = store.messages
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'assistant') return msgs[i].id
  }
  return ''
})

const quickStarts = [
  { icon: '🔍', label: '查看系统状态', text: '帮我看看当前系统状态' },
  { icon: '🧹', label: '检查磁盘空间', text: '帮我检查磁盘空间使用情况' },
  { icon: '📋', label: '查看进程信息', text: '帮我查看占用最高的进程' },
]

// 自动滚动到底部
watch(
  () => store.messages.length,
  () => {
    nextTick(() => {
      if (listRef.value) {
        listRef.value.scrollTo({ top: listRef.value.scrollHeight, behavior: 'smooth' })
      }
    })
  },
)
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--header-height));
}

/* ---- 欢迎引导 ---- */
.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}
.welcome-icon {
  font-size: 56px;
  margin-bottom: 16px;
}
.welcome h2 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}
.welcome-desc {
  color: var(--text-secondary);
  max-width: 400px;
  margin-bottom: 24px;
}
.welcome-actions {
  display: flex;
  gap: 12px;
}
.welcome-card {
  cursor: pointer;
  padding: 12px 20px;
  text-align: center;
  transition: transform 0.2s;
}
.welcome-card:hover {
  transform: translateY(-2px);
}
.card-icon {
  display: block;
  font-size: 24px;
  margin-bottom: 4px;
}

/* ---- 消息列表 ---- */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}
</style>
