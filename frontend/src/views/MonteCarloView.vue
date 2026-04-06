<template>
  <div class="main-view">
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <button class="back-nav" @click="handleGoBack">← </button>
        <span class="logo">MiroFish</span>
        <span class="step-indicator">{{ $t('monteCarlo.title') }}</span>
      </div>
      <div class="header-center">
        <div class="status-indicator" :class="statusClass">
          <span class="status-dot"></span>
          <span class="status-text">{{ statusText }}</span>
        </div>
      </div>
      <div class="header-right">
        <LanguageSwitcher />
      </div>
    </header>

    <!-- Main Content -->
    <main class="content-area">
      <div class="mc-container">
        <!-- 运行阶段：进度面板 -->
        <MonteCarloProgress
          v-if="!showResults"
          :progress="progress"
          @stop="handleStop"
          @view-results="showResults = true"
        />

        <!-- 结果阶段：分析面板 -->
        <MonteCarloResults
          v-else
          :analysis="analysis"
          :groupId="groupId"
          @back="showResults = false"
        />
      </div>
    </main>

    <!-- System Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span>System Logs</span>
        <span class="log-count mono">{{ systemLogs.length }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div v-for="(log, idx) in systemLogs" :key="idx" class="log-entry">
          <span class="log-time mono">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import MonteCarloProgress from '../components/MonteCarloProgress.vue'
import MonteCarloResults from '../components/MonteCarloResults.vue'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import {
  getMonteCarloProgress,
  getMonteCarloAnalysis,
  stopMonteCarloGroup,
} from '../api/monteCarlo'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const groupId = ref(route.params.groupId)
const progress = ref({})
const analysis = ref(null)
const showResults = ref(false)
const systemLogs = ref([])
const logContent = ref(null)

let pollTimer = null

const addLog = (msg) => {
  const now = new Date()
  const time = now.toLocaleTimeString('en-US', { hour12: false }) +
    '.' + String(now.getMilliseconds()).padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 200) systemLogs.value.shift()
  nextTick(() => {
    if (logContent.value) logContent.value.scrollTop = logContent.value.scrollHeight
  })
}

const statusClass = computed(() => {
  const s = progress.value.status
  if (s === 'completed') return 'completed'
  if (s === 'running' || s === 'analyzing') return 'processing'
  if (s === 'failed' || s === 'stopped') return 'error'
  return 'idle'
})

const statusText = computed(() => {
  const s = progress.value.status
  const map = {
    created: t('monteCarlo.statusCreated'),
    running: t('monteCarlo.statusRunning'),
    analyzing: t('monteCarlo.statusAnalyzing'),
    completed: t('monteCarlo.statusCompleted'),
    failed: t('monteCarlo.statusFailed'),
    stopped: t('monteCarlo.statusStopped'),
  }
  return map[s] || s || '...'
})

const fetchProgress = async () => {
  try {
    const res = await getMonteCarloProgress(groupId.value)
    if (res?.success) {
      const prev = progress.value
      progress.value = res.data

      // 状态变化日志
      const p = res.data
      if (prev.completed !== p.completed && p.completed > 0) {
        addLog(`${t('monteCarlo.completed')}: ${p.completed}/${p.total}`)
      }
      if (prev.failed !== p.failed && p.failed > 0) {
        addLog(`${t('monteCarlo.failed')}: ${p.failed}`)
      }

      // 完成或失败时停止轮询
      if (['completed', 'failed', 'stopped'].includes(p.status)) {
        stopPolling()
        addLog(t('monteCarlo.allRunsFinished'))

        // 加载分析结果
        if (p.status === 'completed') {
          await fetchAnalysis()
          showResults.value = true
        }
      }
    }
  } catch (e) {
    // 静默处理轮询错误
  }
}

const fetchAnalysis = async () => {
  try {
    const res = await getMonteCarloAnalysis(groupId.value)
    if (res?.success) {
      analysis.value = res.data
      addLog(t('monteCarlo.analysisLoaded'))
    }
  } catch (e) {
    addLog(t('monteCarlo.analysisNotReady'))
  }
}

const startPolling = () => {
  pollTimer = setInterval(fetchProgress, 3000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const handleStop = async () => {
  addLog(t('monteCarlo.stoppingAll'))
  await stopMonteCarloGroup({ group_id: groupId.value })
  addLog(t('monteCarlo.stopped'))
  await fetchProgress()
}

const handleGoBack = () => {
  stopPolling()
  router.back()
}

onMounted(async () => {
  addLog(`Monte Carlo group: ${groupId.value}`)
  await fetchProgress()

  const s = progress.value.status
  if (s === 'running' || s === 'analyzing') {
    startPolling()
  } else if (s === 'completed') {
    await fetchAnalysis()
    showResults.value = true
  }
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.main-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #fff;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  border-bottom: 1px solid #EAEAEA;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-nav {
  background: none;
  border: none;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.15s;
}

.back-nav:hover {
  color: #333;
  background: #F5F5F5;
}

.logo {
  font-size: 15px;
  font-weight: 700;
  font-family: 'Space Grotesk', sans-serif;
  letter-spacing: -0.5px;
}

.step-indicator {
  font-size: 12px;
  color: #666;
  padding: 3px 10px;
  background: #F5F5F5;
  border-radius: 4px;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #999;
}

.status-indicator.processing .status-dot {
  background: #FF9800;
  animation: pulse 1.5s infinite;
}

.status-indicator.completed .status-dot {
  background: #4CAF50;
}

.status-indicator.error .status-dot {
  background: #F44336;
}

@keyframes pulse {
  50% { opacity: 0.5; }
}

.content-area {
  flex: 1;
  overflow: hidden;
}

.mc-container {
  height: 100%;
  overflow-y: auto;
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

/* System Logs */
.system-logs {
  height: 120px;
  border-top: 1px solid #EAEAEA;
  background: #FAFAFA;
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  padding: 6px 16px;
  font-size: 11px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #EAEAEA;
}

.log-count {
  font-size: 10px;
  color: #CCC;
}

.log-content {
  height: calc(100% - 30px);
  overflow-y: auto;
  padding: 4px 16px;
}

.log-entry {
  display: flex;
  gap: 12px;
  padding: 2px 0;
  font-size: 11px;
}

.log-time {
  color: #CCC;
  flex-shrink: 0;
}

.log-msg {
  color: #666;
}

.header-right {
  display: flex;
  align-items: center;
}
</style>
