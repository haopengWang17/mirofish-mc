<template>
  <div class="mc-progress-panel">
    <!-- 顶部概览 -->
    <div class="overview-bar">
      <div class="overview-stat">
        <span class="stat-value mono completed-val">{{ progress.completed || 0 }}</span>
        <span class="stat-label">{{ $t('monteCarlo.completed') }}</span>
      </div>
      <div class="overview-stat">
        <span class="stat-value mono running-val">{{ progress.running || 0 }}</span>
        <span class="stat-label">{{ $t('monteCarlo.running') }}</span>
      </div>
      <div class="overview-stat">
        <span class="stat-value mono pending-val">{{ progress.pending || 0 }}</span>
        <span class="stat-label">{{ $t('monteCarlo.pending') }}</span>
      </div>
      <div class="overview-stat">
        <span class="stat-value mono failed-val">{{ progress.failed || 0 }}</span>
        <span class="stat-label">{{ $t('monteCarlo.failed') }}</span>
      </div>
    </div>

    <!-- 总进度条 -->
    <div class="overall-progress">
      <div class="progress-header">
        <span class="progress-title">{{ $t('monteCarlo.overallProgress') }}</span>
        <div class="progress-meta">
          <span class="elapsed mono" v-if="elapsed">{{ elapsed }}</span>
          <span class="progress-pct mono">{{ progress.progress_percent || 0 }}%</span>
        </div>
      </div>
      <div class="progress-bar-track">
        <div
          class="progress-bar-fill"
          :style="{ width: (progress.progress_percent || 0) + '%' }"
        ></div>
      </div>
    </div>

    <!-- 子模拟网格 -->
    <div class="children-grid">
      <div
        v-for="(child, idx) in progress.children || []"
        :key="child.child_id"
        class="child-card"
        :class="child.status"
      >
        <div class="child-header">
          <span class="child-index">#{{ idx + 1 }}</span>
          <span class="child-status-badge" :class="child.status">
            {{ getStatusLabel(child.status) }}
          </span>
        </div>
        <div class="child-body">
          <template v-if="child.status === 'running' || child.status === 'starting'">
            <div class="child-progress-bar">
              <div
                class="child-progress-fill"
                :style="{ width: (child.progress_percent || 0) + '%' }"
              ></div>
            </div>
            <div class="child-stats">
              <span class="child-detail mono">R{{ child.current_round || 0 }}/{{ child.total_rounds || '?' }}</span>
              <span class="child-actions mono" v-if="child.twitter_actions_count || child.reddit_actions_count">
                {{ (child.twitter_actions_count || 0) + (child.reddit_actions_count || 0) }} acts
              </span>
            </div>
          </template>
          <template v-else-if="child.status === 'completed' || child.status === 'stopped'">
            <span class="child-detail mono done-text">
              {{ (child.twitter_actions_count || 0) + (child.reddit_actions_count || 0) }} actions
            </span>
          </template>
          <template v-else-if="child.status === 'failed'">
            <span class="child-detail error-text">Error</span>
          </template>
          <template v-else>
            <span class="child-detail muted">{{ $t('monteCarlo.waiting') }}</span>
          </template>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <button
        v-if="progress.status === 'running'"
        class="action-btn danger"
        @click="$emit('stop')"
      >
        {{ $t('monteCarlo.stopAll') }}
      </button>
      <button
        v-if="progress.status === 'completed' || progress.status === 'analyzing'"
        class="action-btn primary"
        @click="$emit('view-results')"
      >
        {{ $t('monteCarlo.viewResults') }} →
      </button>
    </div>

    <!-- 分析中提示 -->
    <div v-if="progress.status === 'analyzing'" class="analyzing-banner">
      <div class="analyzing-spinner"></div>
      <span>{{ $t('monteCarlo.analyzingResults') }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  progress: {
    type: Object,
    default: () => ({}),
  },
})

defineEmits(['stop', 'view-results'])

const startTime = ref(Date.now())
const elapsed = ref('')
let elapsedTimer = null

const updateElapsed = () => {
  const diff = Math.floor((Date.now() - startTime.value) / 1000)
  const m = Math.floor(diff / 60)
  const s = diff % 60
  if (m > 0) {
    elapsed.value = `${m}m ${s}s`
  } else {
    elapsed.value = `${s}s`
  }
}

onMounted(() => {
  elapsedTimer = setInterval(updateElapsed, 1000)
  updateElapsed()
})

onBeforeUnmount(() => {
  if (elapsedTimer) clearInterval(elapsedTimer)
})

const getStatusLabel = (status) => {
  const map = {
    pending: t('monteCarlo.pending'),
    starting: t('monteCarlo.running'),
    running: t('monteCarlo.running'),
    completed: t('monteCarlo.completed'),
    stopped: t('monteCarlo.completed'),
    failed: t('monteCarlo.failed'),
  }
  return map[status] || status
}
</script>

<style scoped>
.mc-progress-panel { padding: 20px; }

.overview-bar { display: flex; gap: 12px; margin-bottom: 20px; }
.overview-stat {
  flex: 1; text-align: center; padding: 14px;
  background: #FAFAFA; border-radius: 10px; border: 1px solid #EAEAEA;
}
.stat-value { display: block; font-size: 28px; font-weight: 700; color: #333; }
.stat-value.completed-val { color: #059669; }
.stat-value.running-val { color: #D97706; }
.stat-value.pending-val { color: #999; }
.stat-value.failed-val { color: #DC2626; }
.stat-label { font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; }
.mono { font-family: 'JetBrains Mono', monospace; }

.overall-progress { margin-bottom: 24px; }
.progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.progress-title { font-size: 13px; font-weight: 600; color: #333; }
.progress-meta { display: flex; gap: 12px; align-items: center; }
.elapsed { font-size: 12px; color: #999; }
.progress-pct { font-size: 13px; color: #333; font-weight: 600; }
.progress-bar-track { height: 8px; background: #EAEAEA; border-radius: 4px; overflow: hidden; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, #059669, #34D399); border-radius: 4px; transition: width 0.5s ease; }

.children-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px; margin-bottom: 20px; max-height: 420px; overflow-y: auto;
}

.child-card {
  padding: 12px; border: 1px solid #EAEAEA; border-radius: 10px;
  background: #fff; transition: all 0.2s;
}
.child-card.running, .child-card.starting { border-color: #FCD34D; background: #FFFBEB; }
.child-card.completed, .child-card.stopped { border-color: #6EE7B7; background: #ECFDF5; }
.child-card.failed { border-color: #FCA5A5; background: #FEF2F2; }

.child-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.child-index { font-size: 13px; font-weight: 700; color: #333; font-family: 'JetBrains Mono', monospace; }

.child-status-badge {
  font-size: 9px; padding: 2px 7px; border-radius: 10px;
  text-transform: uppercase; font-weight: 600; letter-spacing: 0.3px;
}
.child-status-badge.pending { background: #F3F4F6; color: #9CA3AF; }
.child-status-badge.running, .child-status-badge.starting { background: #FEF3C7; color: #B45309; }
.child-status-badge.completed, .child-status-badge.stopped { background: #D1FAE5; color: #065F46; }
.child-status-badge.failed { background: #FEE2E2; color: #991B1B; }

.child-body { min-height: 24px; }
.child-progress-bar { height: 3px; background: #EAEAEA; border-radius: 2px; overflow: hidden; margin-bottom: 4px; }
.child-progress-fill { height: 100%; background: #F59E0B; transition: width 0.5s ease; }
.child-stats { display: flex; justify-content: space-between; align-items: center; }
.child-detail { font-size: 11px; color: #666; }
.child-actions { font-size: 10px; color: #999; }
.child-detail.done-text { color: #059669; }
.child-detail.error-text { color: #DC2626; }
.child-detail.muted { color: #D1D5DB; }

.action-bar { display: flex; justify-content: flex-end; gap: 12px; }
.action-btn {
  padding: 10px 24px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: none; transition: all 0.2s;
}
.action-btn.primary { background: #333; color: #fff; }
.action-btn.primary:hover { background: #000; }
.action-btn.danger { background: #DC2626; color: #fff; }
.action-btn.danger:hover { background: #B91C1C; }

.analyzing-banner {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px; margin-top: 16px;
  background: #FFFBEB; border: 1px solid #FCD34D; border-radius: 10px;
  font-size: 13px; color: #B45309; font-weight: 500;
}
.analyzing-spinner {
  width: 16px; height: 16px;
  border: 2px solid #FCD34D; border-top-color: #B45309;
  border-radius: 50%; animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
