<template>
  <div class="audit-detail">
    <el-empty v-if="!log" description="选择一条日志查看详情" />

    <template v-else>
      <div class="detail-header">
        <StatusBadge :risk-level="log.risk_level" />
        <span class="detail-user">{{ log.user }}</span>
        <span class="detail-time">{{ formatTime(log.timestamp) }}</span>
      </div>

      <el-collapse v-model="activeStages">
        <!-- 阶段 1：接收指令 -->
        <el-collapse-item name="1">
          <template #title>
            <span class="stage-title">📥 接收指令</span>
          </template>
          <blockquote class="stage-block">{{ log.stages[0].raw_input }}</blockquote>
          <p class="stage-meta">用户: {{ log.stages[0].user }} | {{ formatTime(log.stages[0].timestamp) }}</p>
        </el-collapse-item>

        <!-- 阶段 2：感知环境 -->
        <el-collapse-item name="2">
          <template #title>
            <span class="stage-title">🔍 感知环境</span>
          </template>
          <div class="stage-tags">
            <el-tag v-for="t in log.stages[1].tools_called" :key="t" size="small" type="info">{{ t }}</el-tag>
          </div>
          <p class="stage-summary">{{ log.stages[1].snapshot_summary }}</p>
        </el-collapse-item>

        <!-- 阶段 3：推理决策 -->
        <el-collapse-item name="3">
          <template #title>
            <span class="stage-title">🧠 推理决策</span>
          </template>
          <p class="stage-meta">模型: {{ log.stages[2].llm_model }}</p>
          <div class="stage-tags">
            <el-tag v-for="t in log.stages[2].tool_calls_planned" :key="t" size="small" type="warning">{{ t }}</el-tag>
          </div>
          <pre class="llm-output">{{ log.stages[2].llm_raw_output }}</pre>
        </el-collapse-item>

        <!-- 阶段 4：安全校验 -->
        <el-collapse-item name="4">
          <template #title>
            <span class="stage-title">🛡️ 安全校验</span>
          </template>
          <div class="stage-tags">
            <el-tag
              v-for="r in log.stages[3].rules_hit"
              :key="r"
              size="small"
              :type="log.stages[3].rules_hit.length ? 'danger' : 'info'"
            >{{ r || '无规则命中' }}</el-tag>
          </div>
          <div class="risk-score">
            <span>风险评分</span>
            <el-progress
              :percentage="log.stages[3].risk_score"
              :color="scoreColor(log.stages[3].risk_score)"
              :stroke-width="10"
            />
          </div>
          <p class="stage-meta">
            决策: <StatusBadge :risk-level="decisionToRisk(log.stages[3].decision)" size="small" />
            <span class="reason">{{ log.stages[3].reason }}</span>
          </p>
        </el-collapse-item>

        <!-- 阶段 5：执行结果 -->
        <el-collapse-item name="5">
          <template #title>
            <span class="stage-title">⚡ 执行结果</span>
          </template>
          <p class="stage-meta">{{ log.stages[4].action_taken }}</p>
          <p class="stage-meta">
            退出码:
            <el-tag :type="log.stages[4].exit_code === 0 ? 'success' : 'danger'" size="small">
              {{ log.stages[4].exit_code ?? 'N/A' }}
            </el-tag>
            耗时: {{ log.stages[4].duration_ms }}ms
          </p>
          <pre v-if="log.stages[4].stdout" class="output stdout">{{ log.stages[4].stdout }}</pre>
          <pre v-if="log.stages[4].stderr" class="output stderr">{{ log.stages[4].stderr }}</pre>
        </el-collapse-item>
      </el-collapse>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { AuditLog, RiskLevel } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'

defineProps<{ log: AuditLog | null }>()

const activeStages = ref(['1', '4'])

function formatTime(ts: string): string {
  return new Date(ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function scoreColor(s: number): string {
  if (s >= 70) return '#F56C6C'
  if (s >= 40) return '#E6A23C'
  return '#67C23A'
}

function decisionToRisk(d: string): RiskLevel {
  if (d === 'blocked') return 'dangerous'
  if (d === 'confirmed') return 'restricted'
  return 'read_only'
}
</script>

<style scoped>
.audit-detail {
  padding: 16px;
  height: 100%;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.detail-user { font-weight: 600; }
.detail-time { color: var(--text-secondary); font-size: 12px; margin-left: auto; }

.stage-title { font-weight: 600; font-size: 14px; }
.stage-block {
  border-left: 3px solid var(--color-primary);
  padding: 8px 12px;
  margin: 6px 0;
  background: var(--bg-dark);
  border-radius: 4px;
  font-size: 14px;
}
.stage-meta { font-size: 12px; color: var(--text-secondary); margin: 4px 0; }
.stage-summary { font-size: 13px; margin: 6px 0; }
.stage-tags { display: flex; gap: 6px; flex-wrap: wrap; margin: 4px 0; }

.risk-score {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0;
  font-size: 13px;
}
.reason { margin-left: 8px; font-size: 12px; color: var(--text-secondary); }

.llm-output {
  background: #111;
  color: #ccc;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  margin-top: 6px;
}

.output {
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 150px;
  overflow-y: auto;
  white-space: pre-wrap;
  margin-top: 4px;
}
.stdout { background: #111; color: #ccc; }
.stderr { background: #2a1111; color: #f56c6c; }
</style>
