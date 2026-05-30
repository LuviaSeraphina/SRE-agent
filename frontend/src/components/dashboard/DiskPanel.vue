<template>
  <el-card shadow="hover" class="panel">
    <template #header><span class="panel-title">💾 磁盘使用率</span></template>
    <div ref="chartRef" class="chart-box"></div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useSystemStore } from '@/stores/system'

const store = useSystemStore()
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

function barColor(pct: number): string {
  if (pct < 70) return '#67C23A'
  if (pct < 90) return '#E6A23C'
  return '#F56C6C'
}

function updateChart() {
  if (!chart || !store.disks.length) return

  const names = store.disks.map((d) => d.mount_point)
  const values = store.disks.map((d) => +d.usage_percent.toFixed(1))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      confine: true,
      appendToBody: true,
      backgroundColor: 'rgba(30, 32, 34, 0.96)',
      borderColor: '#3a3b3d',
      textStyle: { color: '#e0e0e0', fontSize: 12 },
      extraCssText: 'max-width: 260px; white-space: normal; word-break: break-all; border-radius: 6px; padding: 8px 12px;',
      formatter: (params: { dataIndex: number }[]) => {
        const i = params[0].dataIndex
        const d = store.disks[i]
        return `
          <div style="font-weight:600;margin-bottom:4px;">${d.mount_point} <span style="color:#909399;font-weight:400;">(${d.filesystem})</span></div>
          <div>总量: <b>${d.total_gb} GB</b></div>
          <div>已用: <b>${d.used_gb} GB</b> | 可用: ${d.free_gb} GB</div>
          <div>使用率: <b style="color:${barColor(d.usage_percent)}">${d.usage_percent}%</b> | inode: ${d.inode_percent}%</div>
        `
      },
    },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: '#909399', rotate: names.length > 4 ? 15 : 0 },
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { formatter: '{value}%', color: '#909399' },
    },
    series: [{
      type: 'bar',
      data: values.map((v) => ({
        value: v,
        itemStyle: { color: barColor(v), borderRadius: [4, 4, 0, 0] },
      })),
      barMaxWidth: 50,
      markLine: {
        silent: true,
        symbol: 'none',
        data: [
          { yAxis: 70, lineStyle: { color: '#E6A23C', type: 'dashed' } },
          { yAxis: 90, lineStyle: { color: '#F56C6C', type: 'dashed' } },
        ],
      },
    }],
  })
}

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  updateChart()

  // 自适应容器大小
  resizeObserver = new ResizeObserver(() => {
    chart?.resize()
  })
  resizeObserver.observe(chartRef.value)
})

watch(() => store.disks, updateChart, { deep: true })

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
})
</script>

<style scoped>
.panel { height: 100%; }
.chart-box {
  width: 100%;
  height: 240px;
}
.panel-title { font-size: 15px; font-weight: 600; }
</style>
