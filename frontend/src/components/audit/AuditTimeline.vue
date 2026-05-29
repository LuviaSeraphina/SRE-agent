<template>
  <div class="timeline-wrap" v-loading="loading">
    <el-empty v-if="!loading && logs.length === 0" description="暂无审计记录" />

    <el-timeline v-else>
      <el-timeline-item
        v-for="log in logs"
        :key="log.id"
        :timestamp="formatTime(log.timestamp)"
        :color="nodeColor(log.risk_level)"
        placement="top"
      >
        <div class="timeline-node" :class="{ selected: selectedId === log.id }" @click="onSelect(log)">
          <StatusBadge :risk-level="log.risk_level" size="small" />
          <span class="node-user">{{ log.user }}</span>
          <span class="node-summary">{{ summary(log) }}</span>
        </div>
      </el-timeline-item>
    </el-timeline>

    <el-pagination
      v-if="total > filter.size"
      class="pagination"
      background
      layout="total, prev, pager, next"
      :total="total"
      :page-size="filter.size"
      :current-page="filter.page"
      @current-change="emit('pageChange', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AuditLog, RiskLevel } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'

const props = defineProps<{
  logs: AuditLog[]
  loading: boolean
  total: number
  filter: { page: number; size: number }
  selectedId: string | null
}>()

const emit = defineEmits<{
  select: [log: AuditLog]
  pageChange: [page: number]
}>()

function formatTime(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function nodeColor(risk: RiskLevel): string {
  if (risk === 'dangerous') return '#F56C6C'
  if (risk === 'restricted') return '#E6A23C'
  return '#67C23A'
}

function summary(log: AuditLog): string {
  const raw = log.stages[0]?.raw_input || ''
  return raw.length > 60 ? raw.slice(0, 60) + '...' : raw
}

function onSelect(log: AuditLog) {
  emit('select', log)
}
</script>

<style scoped>
.timeline-wrap {
  padding: 16px;
}

.timeline-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}
.timeline-node:hover {
  background: rgba(64, 158, 255, 0.06);
}
.timeline-node.selected {
  background: rgba(64, 158, 255, 0.1);
}

.node-user {
  font-weight: 600;
  font-size: 13px;
}
.node-summary {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination {
  margin-top: 16px;
  justify-content: center;
}
</style>
