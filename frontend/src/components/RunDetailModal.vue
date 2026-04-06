<template>
  <div v-if="visible" class="run-modal-overlay" @click.self="$emit('close')">
    <div class="run-modal">
      <!-- Header -->
      <div class="modal-header">
        <div class="header-info">
          <h3>{{ $t('monteCarlo.runDetail') }} #{{ runIndex + 1 }}</h3>
          <span v-if="categoryName" class="category-badge" :style="{ background: categoryColor }">
            {{ categoryName }}
          </span>
        </div>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <!-- Outcome Summary -->
      <div class="outcome-section">
        <div class="outcome-label">{{ $t('monteCarlo.outcomeResult') }}</div>
        <p class="outcome-text">{{ run?.outcome_summary || '—' }}</p>
      </div>

      <!-- Stats Row -->
      <div class="stats-row">
        <div class="mini-stat">
          <span class="mini-val mono">{{ run?.total_posts || 0 }}</span>
          <span class="mini-label">{{ $t('monteCarlo.statPosts') }}</span>
        </div>
        <div class="mini-stat">
          <span class="mini-val mono">{{ run?.total_likes || 0 }}</span>
          <span class="mini-label">{{ $t('monteCarlo.statLikes') }}</span>
        </div>
        <div class="mini-stat">
          <span class="mini-val mono">{{ run?.total_comments || 0 }}</span>
          <span class="mini-label">{{ $t('monteCarlo.statComments') }}</span>
        </div>
        <div class="mini-stat">
          <span class="mini-val mono">{{ run?.total_reposts || 0 }}</span>
          <span class="mini-label">{{ $t('monteCarlo.statReposts') }}</span>
        </div>
        <div class="mini-stat">
          <span class="mini-val mono">{{ run?.total_actions || 0 }}</span>
          <span class="mini-label">{{ $t('monteCarlo.statTotalActions') }}</span>
        </div>
      </div>

      <!-- Tab Switcher -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span v-if="tab.count !== undefined" class="tab-count mono">{{ tab.count }}</span>
        </button>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        <!-- Posts Tab -->
        <div v-if="activeTab === 'posts'" class="posts-section">
          <div v-if="loading" class="loading-state">
            <div class="spinner"></div>
            <span>{{ $t('common.loading') }}</span>
          </div>
          <div v-else-if="posts.length" class="posts-list">
            <div v-for="(post, idx) in posts" :key="idx" class="post-card">
              <div class="post-header">
                <span class="post-agent">{{ post.agent_name }}</span>
                <span class="post-platform" :class="post.platform">{{ post.platform }}</span>
                <span class="post-round mono">R{{ post.round_num }}</span>
              </div>
              <div class="post-content">{{ post.content }}</div>
            </div>
          </div>
          <div v-else class="empty-state">{{ $t('monteCarlo.noPosts') }}</div>
        </div>

        <!-- Agent Activity Tab -->
        <div v-if="activeTab === 'agents'" class="agents-section">
          <div v-if="run?.agent_activity" class="agent-list">
            <div v-for="(count, name) in run.agent_activity" :key="name" class="agent-row">
              <span class="agent-name">{{ name }}</span>
              <div class="agent-bar-wrap">
                <div class="agent-bar" :style="{ width: (count / maxAgentCount * 100) + '%' }"></div>
              </div>
              <span class="agent-count mono">{{ count }}</span>
            </div>
          </div>
          <div v-else class="empty-state">No agent data</div>
        </div>

        <!-- Action Types Tab -->
        <div v-if="activeTab === 'actions'" class="actions-section">
          <div v-if="run?.action_type_counts" class="action-type-list">
            <div v-for="(count, type) in run.action_type_counts" :key="type" class="action-type-row">
              <span class="action-type-name">{{ type }}</span>
              <div class="action-bar-wrap">
                <div class="action-bar" :style="{ width: (count / maxActionCount * 100) + '%' }"></div>
              </div>
              <span class="action-count mono">{{ count }}</span>
            </div>
          </div>
          <div v-else class="empty-state">No action data</div>
        </div>
      </div>

      <!-- Actions -->
      <div class="modal-actions">
        <button class="action-btn primary" @click="handleGenerateReport" :disabled="reportLoading">
          {{ reportLoading ? $t('monteCarlo.generatingReport') : $t('monteCarlo.generateRunReport') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { getSimulationActions } from '../api/simulation'
import { generateReport } from '../api/report'

const { t } = useI18n()
const router = useRouter()

const props = defineProps({
  visible: Boolean,
  run: Object,
  runIndex: { type: Number, default: 0 },
  categoryName: { type: String, default: '' },
  categoryColor: { type: String, default: '#666' },
})

const emit = defineEmits(['close', 'report-generated'])

const posts = ref([])
const loading = ref(false)
const reportLoading = ref(false)
const activeTab = ref('posts')

const tabs = computed(() => [
  { key: 'posts', label: t('monteCarlo.statPosts'), count: posts.value.length },
  { key: 'agents', label: 'Agents', count: Object.keys(props.run?.agent_activity || {}).length },
  { key: 'actions', label: t('monteCarlo.statTotalActions'), count: props.run?.total_actions || 0 },
])

const maxAgentCount = computed(() => {
  const vals = Object.values(props.run?.agent_activity || {})
  return Math.max(...vals, 1)
})

const maxActionCount = computed(() => {
  const vals = Object.values(props.run?.action_type_counts || {})
  return Math.max(...vals, 1)
})

const fetchPosts = async () => {
  if (!props.run?.child_id) return
  loading.value = true
  posts.value = []

  try {
    const res = await getSimulationActions(props.run.child_id, {
      limit: 100,
    })
    if (res?.success && res.data?.actions) {
      posts.value = res.data.actions
        .filter(a => a.action_type === 'CREATE_POST' || a.action_type === 'CREATE_COMMENT')
        .map(a => ({
          agent_name: a.agent_name || 'Unknown',
          platform: a.platform || 'twitter',
          round_num: a.round_num || 0,
          content: a.action_args?.content || a.result || '—',
          action_type: a.action_type,
        }))
    }
  } catch (e) {
    if (props.run?.sample_posts) {
      posts.value = props.run.sample_posts.map((content, i) => ({
        agent_name: 'Agent',
        platform: 'twitter',
        round_num: i,
        content,
      }))
    }
  } finally {
    loading.value = false
  }
}

const handleGenerateReport = async () => {
  if (!props.run?.child_id) return
  reportLoading.value = true
  try {
    const res = await generateReport({
      simulation_id: props.run.child_id,
      force_regenerate: true,
    })
    if (res?.success) {
      const reportId = res.data.report_id
      emit('report-generated', reportId)
      const url = router.resolve({
        name: 'Report',
        params: { reportId },
      }).href
      window.open(url, '_blank')
    }
  } catch (e) {
    console.error('Report generation failed:', e)
  } finally {
    reportLoading.value = false
  }
}

watch(() => props.visible, (val) => {
  if (val) {
    activeTab.value = 'posts'
    fetchPosts()
  }
})
</script>

<style scoped>
.run-modal-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; backdrop-filter: blur(3px);
}
.run-modal {
  background: #fff; border-radius: 14px; width: 680px; max-width: 92vw;
  max-height: 88vh; display: flex; flex-direction: column;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 18px 24px; border-bottom: 1px solid #EAEAEA;
  flex-shrink: 0;
}
.header-info { display: flex; align-items: center; gap: 12px; }
.header-info h3 { font-size: 16px; font-weight: 700; margin: 0; font-family: 'Space Grotesk', sans-serif; }
.category-badge { font-size: 11px; padding: 3px 10px; border-radius: 12px; color: #fff; font-weight: 600; }
.close-btn { background: none; border: none; font-size: 22px; cursor: pointer; color: #999; padding: 4px 8px; line-height: 1; }

.outcome-section { padding: 16px 24px 12px; flex-shrink: 0; }
.outcome-label { font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; font-weight: 600; }
.outcome-text { font-size: 14px; color: #333; line-height: 1.6; margin: 0; padding: 12px 16px; background: #F8F9FA; border-radius: 8px; border-left: 3px solid #333; }

.stats-row { display: flex; gap: 6px; padding: 0 24px 12px; flex-shrink: 0; }
.mini-stat { flex: 1; text-align: center; padding: 6px 4px; background: #FAFAFA; border-radius: 6px; }
.mini-val { display: block; font-size: 16px; font-weight: 700; color: #333; }
.mini-label { font-size: 9px; color: #999; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* Tabs */
.tab-bar { display: flex; gap: 0; padding: 0 24px; border-bottom: 1px solid #EAEAEA; flex-shrink: 0; }
.tab-btn {
  padding: 8px 16px; font-size: 12px; font-weight: 600; color: #999;
  border: none; background: none; cursor: pointer;
  border-bottom: 2px solid transparent; transition: all 0.15s;
}
.tab-btn.active { color: #333; border-bottom-color: #333; }
.tab-btn:hover { color: #666; }
.tab-count { font-size: 10px; color: #CCC; margin-left: 4px; }

/* Tab Content */
.tab-content { flex: 1; overflow-y: auto; padding: 16px 24px; }

.posts-list { display: flex; flex-direction: column; gap: 8px; }
.post-card { padding: 10px 14px; background: #FAFAFA; border: 1px solid #EAEAEA; border-radius: 8px; }
.post-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.post-agent { font-size: 12px; font-weight: 600; color: #333; }
.post-platform { font-size: 9px; padding: 1px 6px; border-radius: 3px; text-transform: uppercase; font-weight: 600; }
.post-platform.twitter { background: #E3F2FD; color: #1565C0; }
.post-platform.reddit { background: #FFF3E0; color: #E65100; }
.post-round { font-size: 10px; color: #999; margin-left: auto; }
.post-content { font-size: 13px; color: #555; line-height: 1.5; }

/* Agent Activity */
.agent-list { display: flex; flex-direction: column; gap: 6px; }
.agent-row { display: flex; align-items: center; gap: 10px; }
.agent-name { font-size: 12px; color: #333; width: 120px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-bar-wrap { flex: 1; height: 6px; background: #EAEAEA; border-radius: 3px; overflow: hidden; }
.agent-bar { height: 100%; background: #2563EB; border-radius: 3px; transition: width 0.3s; }
.agent-count { font-size: 11px; color: #999; min-width: 30px; text-align: right; }

/* Action Types */
.action-type-list { display: flex; flex-direction: column; gap: 6px; }
.action-type-row { display: flex; align-items: center; gap: 10px; }
.action-type-name { font-size: 11px; color: #333; width: 130px; flex-shrink: 0; font-family: 'JetBrains Mono', monospace; }
.action-bar-wrap { flex: 1; height: 6px; background: #EAEAEA; border-radius: 3px; overflow: hidden; }
.action-bar { height: 100%; background: #059669; border-radius: 3px; transition: width 0.3s; }
.action-count { font-size: 11px; color: #999; min-width: 30px; text-align: right; }

.loading-state, .empty-state { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 32px; color: #999; font-size: 13px; }
.spinner { width: 16px; height: 16px; border: 2px solid #EEE; border-top-color: #333; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.modal-actions {
  display: flex; gap: 12px; padding: 14px 24px;
  border-top: 1px solid #EAEAEA; flex-shrink: 0;
}
.action-btn {
  flex: 1; padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: none; transition: all 0.2s;
}
.action-btn.primary { background: #333; color: #fff; }
.action-btn.primary:hover { background: #000; }
.action-btn.primary:disabled { background: #CCC; cursor: not-allowed; }
</style>
