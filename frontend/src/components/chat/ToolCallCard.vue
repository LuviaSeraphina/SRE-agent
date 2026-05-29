<template>
  <div class="tool-card" :class="[`status-${toolCall.status}`]">
    <!-- 折叠状态：工具名 + 状态 -->
    <div class="tool-header" @click="expanded = !expanded">
      <span class="tool-icon">{{ statusIcon }}</span>
      <span class="tool-name">{{ toolCall.tool_name }}</span>
      <StatusBadge v-if="toolCall.risk_level" :risk-level="toolCall.risk_level" size="small" />
      <el-icon class="expand-arrow" :class="{ expanded }"><ArrowRight /></el-icon>
    </div>

    <!-- 展开状态：参数 + 结果 -->
    <el-collapse-transition>
      <div v-show="expanded" class="tool-detail">
        <div class="detail-row">
          <span class="label">参数</span>
          <pre class="json-block">{{ formattedArgs }}</pre>
        </div>
        <div class="detail-row" v-if="toolCall.result !== undefined">
          <span class="label">结果</span>
          <pre class="json-block">{{ formattedResult }}</pre>
        </div>
      </div>
    </el-collapse-transition>

    <!-- 运行中进度条 -->
    <el-progress
      v-if="toolCall.status === 'running'"
      :percentage="100"
      :indeterminate="true"
      :show-text="false"
      :stroke-width="2"
      class="running-bar"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import type { ToolCall } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'

const props = defineProps<{ toolCall: ToolCall }>()
const expanded = ref(false)

const statusIcon = computed(() => {
  switch (props.toolCall.status) {
    case 'pending': return '⏳'
    case 'running': return '🔄'
    case 'done':    return '✅'
    case 'error':   return '❌'
    default:        return '🔧'
  }
})

const formattedArgs = computed(() => {
  try {
    return JSON.stringify(props.toolCall.arguments, null, 2)
  } catch {
    return String(props.toolCall.arguments)
  }
})

const formattedResult = computed(() => {
  if (typeof props.toolCall.result === 'string') return props.toolCall.result
  try {
    return JSON.stringify(props.toolCall.result, null, 2)
  } catch {
    return String(props.toolCall.result)
  }
})
</script>

<style scoped>
.tool-card {
  background: var(--bg-dark);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  overflow: hidden;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
  transition: background 0.15s;
}
.tool-header:hover {
  background: rgba(64, 158, 255, 0.06);
}

.tool-icon {
  font-size: 14px;
}
.tool-name {
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-weight: 600;
  flex: 1;
}

.expand-arrow {
  transition: transform 0.2s;
  font-size: 12px;
  color: var(--text-secondary);
}
.expand-arrow.expanded {
  transform: rotate(90deg);
}

/* 状态着色 */
.status-running {
  border-left: 3px solid var(--color-primary);
}
.status-done {
  border-left: 3px solid var(--color-safe);
}
.status-error {
  border-left: 3px solid var(--color-danger);
}

/* 详情 */
.tool-detail {
  padding: 0 10px 10px;
}
.detail-row {
  margin-top: 8px;
}
.label {
  display: block;
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.json-block {
  background: #111;
  color: #ccc;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 160px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.running-bar {
  margin: 0;
}
</style>
