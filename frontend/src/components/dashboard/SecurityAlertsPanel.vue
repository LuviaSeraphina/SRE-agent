<template>
  <div class="panel-card">
    <div class="panel-header">
      <h3 class="panel-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
        安全告警
      </h3>
      <span v-if="hasNoAlerts" class="panel-badge safe">无告警</span>
      <span v-else class="panel-badge warn">{{ alerts.length }} 条</span>
    </div>

    <div v-if="hasNoAlerts" class="empty-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="1.5" stroke-linecap="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      <span>当前无安全告警</span>
    </div>

    <div v-else class="alerts-body">
      <div class="alert-section">
        <span class="section-label">安全扫描结果</span>
        <div class="alert-list">
          <div
            v-for="alert in alerts"
            :key="`${alert.tool}-${alert.title}-${alert.detail}`"
            class="alert-item"
            :class="alert.severity"
          >
            <div class="alert-head">
              <span class="alert-tool">{{ alert.title }}</span>
              <span class="alert-severity">{{ severityLabel(alert.severity) }}</span>
            </div>
            <p class="alert-detail">{{ alert.detail }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSystemStore } from '@/stores/system'

const store = useSystemStore()

const alerts = computed(() => store.snapshot.securityAlerts ?? [])
const hasNoAlerts = computed(() => alerts.value.length === 0)

function severityLabel(severity: 'info' | 'warning' | 'danger'): string {
  switch (severity) {
    case 'danger':
      return '高危'
    case 'warning':
      return '警告'
    default:
      return '提示'
  }
}
</script>

<style scoped>
.panel-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color var(--dur-gentle) var(--ease-out);
}
.panel-card:hover {
  border-color: var(--border-emphasis);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-badge {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}
.panel-badge.safe { color: var(--color-safe); background: var(--color-safe-soft); }
.panel-badge.warn { color: var(--color-warning); background: var(--color-warning-soft); }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 36px 20px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.alerts-body {
  padding: 16px 20px;
}

.alert-section {
  margin-bottom: 18px;
}
.alert-section:last-child {
  margin-bottom: 0;
}
.section-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.alert-item {
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  border: 1px solid transparent;
  background: var(--bg-elevated);
}
.alert-item.warning {
  border-color: var(--color-warning-soft);
}
.alert-item.danger {
  border-color: var(--color-danger-soft);
}
.alert-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.alert-tool {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.alert-severity {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.4px;
  color: var(--text-tertiary);
}
.alert-detail {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
}
</style>
