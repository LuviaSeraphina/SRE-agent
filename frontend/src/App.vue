<template>
  <el-container class="app-root">
    <!-- 网络断开提示 -->
    <el-alert
      v-if="offline"
      title="网络连接已断开，请检查网络"
      type="error"
      :closable="false"
      show-icon
      class="offline-bar"
    />

    <!-- 侧边栏 -->
    <el-aside :width="sidebarWidth">
      <AppSidebar />
    </el-aside>

    <!-- 右侧区域 -->
    <el-container>
      <!-- 顶部状态栏 -->
      <el-header height="var(--header-height)" class="app-header">
        <SystemOverview />
      </el-header>

      <!-- 主内容区 -->
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import AppSidebar from '@/components/common/AppSidebar.vue'
import SystemOverview from '@/components/common/SystemOverview.vue'

const sidebarWidth = '220px'
const offline = ref(!navigator.onLine)

function onOnline()  { offline.value = false }
function onOffline() { offline.value = true  }

onMounted(() => {
  window.addEventListener('online',  onOnline)
  window.addEventListener('offline', onOffline)
})

onUnmounted(() => {
  window.removeEventListener('online',  onOnline)
  window.removeEventListener('offline', onOffline)
})
</script>

<style scoped>
.app-root {
  height: 100vh;
  position: relative;
}

.offline-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 3000;
  border-radius: 0;
}

.app-header {
  padding: 0;
}

.app-main {
  background-color: var(--bg-dark);
  overflow-y: auto;
  padding: 0;
}
</style>
