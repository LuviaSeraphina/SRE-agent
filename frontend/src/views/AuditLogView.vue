<template>
  <div class="audit-page">
    <!-- 筛选器 -->
    <AuditFilter @filter-change="onFilterChange" />

    <!-- 左右分栏 -->
    <div class="audit-body">
      <div class="audit-left">
        <AuditTimeline
          :logs="store.logs"
          :loading="store.loading"
          :total="store.total"
          :filter="{ page: store.filter.page, size: store.filter.size }"
          :selected-id="selectedId"
          @select="selectedId = $event.id"
          @page-change="onPageChange"
        />
      </div>
      <div class="audit-right">
        <AuditDetail :log="selectedLog" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuditStore } from '@/stores/audit'
import AuditFilter from '@/components/audit/AuditFilter.vue'
import AuditTimeline from '@/components/audit/AuditTimeline.vue'
import AuditDetail from '@/components/audit/AuditDetail.vue'
import type { RiskLevel } from '@/types'

const store = useAuditStore()
const selectedId = ref<string | null>(null)

const selectedLog = computed(() => {
  if (!selectedId.value) return null
  return store.logs.find((l) => l.id === selectedId.value) ?? null
})

function onFilterChange(params: { keyword: string; riskLevel: string; dateRange: string[] | null }) {
  store.setFilter({
    keyword: params.keyword,
    risk_level: (params.riskLevel || '') as RiskLevel | '',
  })
  store.loadLogs()
  selectedId.value = null
}

function onPageChange(page: number) {
  store.setPage(page)
  store.loadLogs()
  selectedId.value = null
}

onMounted(() => {
  store.loadLogs()
})
</script>

<style scoped>
.audit-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--header-height));
}

.audit-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.audit-left {
  width: 60%;
  overflow-y: auto;
  border-right: 1px solid var(--border-color);
}

.audit-right {
  width: 40%;
  overflow-y: auto;
}
</style>
