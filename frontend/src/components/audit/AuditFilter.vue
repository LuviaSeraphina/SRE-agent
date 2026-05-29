<template>
  <el-form :inline="true" class="audit-filter" @submit.prevent="onSearch">
    <el-form-item>
      <el-input
        v-model="keyword"
        placeholder="搜索指令关键字或用户名..."
        clearable
        :prefix-icon="Search"
        style="width: 240px"
        @clear="onSearch"
      />
    </el-form-item>

    <el-form-item>
      <el-select v-model="riskLevel" placeholder="风险等级" clearable style="width: 150px" @change="onSearch">
        <el-option label="全部" value="" />
        <el-option label="🟢 安全" value="read_only" />
        <el-option label="🟡 需确认" value="restricted" />
        <el-option label="🔴 高危" value="dangerous" />
      </el-select>
    </el-form-item>

    <el-form-item>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        style="width: 260px"
        @change="onSearch"
      />
    </el-form-item>

    <el-form-item>
      <el-button type="primary" @click="onSearch">查询</el-button>
      <el-button @click="onReset">重置</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'

const emit = defineEmits<{
  filterChange: [params: { keyword: string; riskLevel: string; dateRange: string[] | null }]
}>()

const keyword = ref('')
const riskLevel = ref('')
const dateRange = ref<string[] | null>(null)

function onSearch() {
  emit('filterChange', {
    keyword: keyword.value,
    riskLevel: riskLevel.value,
    dateRange: dateRange.value,
  })
}

function onReset() {
  keyword.value = ''
  riskLevel.value = ''
  dateRange.value = null
  onSearch()
}
</script>

<style scoped>
.audit-filter {
  padding: 12px 16px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 0;
}
</style>
