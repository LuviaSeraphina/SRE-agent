<template>
  <el-dialog
    :model-value="!!store.pendingConfirm"
    title="⚠️ 危险操作确认"
    width="480px"
    :close-on-click-modal="false"
    @close="store.clearPendingConfirm()"
  >
    <div v-if="store.pendingConfirm" class="confirm-body">
      <div class="confirm-row">
        <span class="label">工具</span>
        <code class="tool-name">{{ store.pendingConfirm.tool_name }}</code>
      </div>
      <div class="confirm-row">
        <span class="label">风险</span>
        <StatusBadge :risk-level="store.pendingConfirm.risk_level" />
      </div>
      <div class="confirm-row">
        <span class="label">摘要</span>
        <span>{{ store.pendingConfirm.summary }}</span>
      </div>
      <el-collapse class="detail-collapse">
        <el-collapse-item title="查看详情">
          <p class="detail-text">{{ store.pendingConfirm.details }}</p>
        </el-collapse-item>
      </el-collapse>
    </div>

    <template #footer>
      <el-button @click="store.clearPendingConfirm()">取消</el-button>
      <el-button
        type="danger"
        :disabled="confirming"
        @click="handleConfirm"
      >
        {{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { confirmAction } from '@/api/chat'
import StatusBadge from '@/components/common/StatusBadge.vue'

const store = useChatStore()
const confirming = ref(false)
const confirmCount = ref(0)

const confirmText = ref('确认执行')

async function handleConfirm() {
  confirmCount.value++
  if (confirmCount.value < 2) {
    confirmText.value = '再次确认'
    setTimeout(() => {
      if (confirmCount.value < 2) {
        confirmText.value = '确认执行'
        confirmCount.value = 0
      }
    }, 1500)
    return
  }

  if (!store.pendingConfirm) return
  confirming.value = true
  try {
    await confirmAction(store.currentSessionId, store.pendingConfirm.message_id)
  } catch (e) {
    console.error('确认操作失败:', e)
  } finally {
    confirming.value = false
    confirmCount.value = 0
    confirmText.value = '确认执行'
    store.clearPendingConfirm()
  }
}
</script>

<style scoped>
.confirm-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.confirm-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.label {
  font-size: 13px;
  color: var(--text-secondary);
  min-width: 40px;
}
.tool-name {
  font-family: 'Consolas', monospace;
  background: var(--bg-dark);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
}
.detail-collapse {
  margin-top: 4px;
}
.detail-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}
</style>
