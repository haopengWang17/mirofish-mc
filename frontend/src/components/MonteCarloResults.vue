<template>
  <div class="mc-results-panel">
    <!-- 返回按钮 -->
    <div class="results-header">
      <button class="back-btn" @click="$emit('back')">← {{ $t('monteCarlo.backToProgress') }}</button>
      <h2 class="results-title">{{ $t('monteCarlo.analysisTitle') }}</h2>
    </div>

    <template v-if="analysis">
      <!-- 关键洞察 -->
      <div class="key-insight-banner" v-if="analysis.key_insight">
        <div class="insight-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </div>
        <div class="insight-content">
          <span class="insight-label">{{ $t('monteCarlo.keyInsight') }}</span>
          <span class="insight-text">{{ analysis.key_insight }}</span>
        </div>
      </div>

      <!-- 收敛指数 + 统计概览 -->
      <div class="overview-row">
        <div class="convergence-gauge">
          <div class="gauge-circle">
            <svg viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" fill="none" stroke="#EAEAEA" stroke-width="6"/>
              <circle cx="50" cy="50" r="42" fill="none"
                :stroke="convergenceColor"
                stroke-width="6"
                stroke-linecap="round"
                :stroke-dasharray="convergenceDash"
                transform="rotate(-90 50 50)"/>
            </svg>
            <div class="gauge-value">
              <span class="gauge-num mono">{{ convergencePercent }}</span>
              <span class="gauge-unit">%</span>
            </div>
          </div>
          <span class="gauge-label">{{ $t('monteCarlo.convergenceIndex') }}</span>
        </div>
        <div class="stats-compact">
          <div v-for="(stats, key) in mainStats" :key="key" class="stat-pill">
            <span class="pill-key">{{ formatStatKey(key) }}</span>
            <span class="pill-val mono">{{ stats.mean }}<span class="pill-std">±{{ stats.std }}</span></span>
          </div>
        </div>
      </div>

      <!-- 结果分类 -->
      <div class="categories-section">
        <h3 class="section-title">{{ $t('monteCarlo.outcomeCategories') }}</h3>
        <div class="category-cards">
          <div
            v-for="(cat, idx) in analysis.outcome_categories"
            :key="idx"
            class="category-card"
            :class="{ active: selectedCategory === idx }"
            :style="{ borderLeftColor: COLORS[idx % COLORS.length] }"
            @click="selectedCategory = selectedCategory === idx ? null : idx"
          >
            <div class="cat-header">
              <span class="cat-color" :style="{ background: COLORS[idx % COLORS.length] }"></span>
              <span class="cat-name">{{ cat.category_name }}</span>
              <span class="cat-pct mono">{{ cat.count }}/{{ analysis.total_runs_analyzed }} ({{ cat.percentage }}%)</span>
            </div>
            <p class="cat-desc">{{ cat.description }}</p>
            <p v-if="selectedCategory === idx" class="cat-summary">{{ cat.representative_summary }}</p>
          </div>
        </div>
      </div>

      <!-- 每次运行的结局（可点击） -->
      <div class="run-outcomes-section">
        <h3 class="section-title">{{ $t('monteCarlo.eachRunOutcome') }}</h3>
        <div class="outcomes-list">
          <div
            v-for="(m, idx) in analysis.run_metrics"
            :key="m.child_id"
            class="outcome-row clickable"
            @click="openRunDetail(idx)"
          >
            <span class="outcome-index mono">#{{ idx + 1 }}</span>
            <span
              class="outcome-cat-dot"
              :style="{ background: getRunCategoryColor(m.child_id) }"
              :title="getRunCategoryName(m.child_id)"
            ></span>
            <span class="outcome-text">{{ m.outcome_summary || '—' }}</span>
            <span class="outcome-arrow">→</span>
          </div>
        </div>
      </div>

      <!-- 分布图 -->
      <div class="distributions-section">
        <h3 class="section-title">{{ $t('monteCarlo.metricDistributions') }}</h3>
        <div class="charts-grid">
          <div v-for="key in distributionKeys" :key="key" class="chart-wrapper">
            <MCDistributionChart
              :data="getMetricValues(key)"
              :label="formatStatKey(key)"
              :color="'#333'"
              :width="360"
              :height="180"
            />
          </div>
        </div>
      </div>

      <!-- 导出报告 -->
      <div class="report-section">
        <button class="action-btn primary full-width" @click="handleExportReport">
          {{ $t('monteCarlo.exportReport') }}
        </button>
      </div>
    </template>

    <div v-else class="no-analysis">
      <p>{{ $t('monteCarlo.noAnalysis') }}</p>
    </div>

    <!-- Run Detail Modal -->
    <RunDetailModal
      :visible="showRunDetail"
      :run="selectedRun"
      :runIndex="selectedRunIndex"
      :categoryName="selectedRunCategoryName"
      :categoryColor="selectedRunCategoryColor"
      @close="showRunDetail = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import * as d3 from 'd3'
import MCDistributionChart from './charts/MCDistributionChart.vue'
import RunDetailModal from './RunDetailModal.vue'

const { t } = useI18n()

const props = defineProps({
  analysis: Object,
  groupId: String,
})

defineEmits(['back'])

const COLORS = ['#2563EB', '#DC2626', '#059669', '#D97706', '#7C3AED', '#DB2777']

const selectedCategory = ref(null)
const pieContainer = ref(null)
const showRunDetail = ref(false)
const selectedRun = ref(null)
const selectedRunIndex = ref(0)

const mainStats = computed(() => {
  if (!props.analysis?.aggregate) return {}
  const agg = props.analysis.aggregate
  const keys = ['total_actions', 'total_posts', 'total_likes', 'total_comments', 'total_reposts']
  const result = {}
  for (const key of keys) {
    if (agg[key]) result[key] = agg[key]
  }
  return result
})

const distributionKeys = computed(() => Object.keys(mainStats.value))

const convergencePercent = computed(() => {
  const ci = props.analysis?.aggregate?.convergence_index || 0
  return Math.round(ci * 100)
})

const convergenceColor = computed(() => {
  const p = convergencePercent.value
  if (p >= 70) return '#059669'
  if (p >= 40) return '#D97706'
  return '#DC2626'
})

const convergenceDash = computed(() => {
  const circumference = 2 * Math.PI * 42
  const pct = (props.analysis?.aggregate?.convergence_index || 0)
  return `${circumference * pct} ${circumference * (1 - pct)}`
})

const formatStatKey = (key) => {
  const map = {
    total_actions: t('monteCarlo.statTotalActions'),
    twitter_actions: 'Twitter',
    reddit_actions: 'Reddit',
    total_posts: t('monteCarlo.statPosts'),
    total_likes: t('monteCarlo.statLikes'),
    total_comments: t('monteCarlo.statComments'),
    total_reposts: t('monteCarlo.statReposts'),
    total_rounds: t('monteCarlo.statRounds'),
  }
  return map[key] || key
}

const formatChildId = (childId) => {
  const match = childId.match(/_mc(\d+)$/)
  return match ? `#${parseInt(match[1]) + 1}` : childId
}

const getMetricValues = (key) => {
  if (!props.analysis?.run_metrics) return []
  return props.analysis.run_metrics.map(m => m[key] || 0)
}

// 获取 run 所属分类的颜色
const getRunCategoryColor = (childId) => {
  if (!props.analysis?.outcome_categories) return '#999'
  for (let i = 0; i < props.analysis.outcome_categories.length; i++) {
    const cat = props.analysis.outcome_categories[i]
    if (cat.child_ids?.includes(childId)) {
      return COLORS[i % COLORS.length]
    }
  }
  return '#999'
}

const getRunCategoryName = (childId) => {
  if (!props.analysis?.outcome_categories) return ''
  for (const cat of props.analysis.outcome_categories) {
    if (cat.child_ids?.includes(childId)) return cat.category_name
  }
  return ''
}

const selectedRunCategoryName = computed(() => {
  if (!selectedRun.value) return ''
  return getRunCategoryName(selectedRun.value.child_id)
})

const selectedRunCategoryColor = computed(() => {
  if (!selectedRun.value) return '#666'
  return getRunCategoryColor(selectedRun.value.child_id)
})

const openRunDetail = (idx) => {
  selectedRun.value = props.analysis.run_metrics[idx]
  selectedRunIndex.value = idx
  showRunDetail.value = true
}

const handleExportReport = () => {
  if (!props.analysis) return

  const a = props.analysis
  const cats = a.outcome_categories || []
  const runs = a.run_metrics || []
  const agg = a.aggregate || {}
  const ci = agg.convergence_index

  let md = `# Monte Carlo Simulation Report\n\n`
  if (a.key_insight) {
    md += `> **${a.key_insight}**\n\n`
  }
  md += `${a.total_runs_analyzed} runs analyzed | Convergence: ${(ci * 100).toFixed(1)}% | ${new Date(a.analyzed_at).toLocaleString()}\n\n`
  md += `---\n\n`

  md += `## Outcome Categories\n\n`
  for (const c of cats) {
    md += `### ${c.category_name} — ${c.count} runs (${c.percentage}%)\n\n`
    md += `${c.description}\n\n`
    md += `> ${c.representative_summary}\n\n`
  }

  md += `## Each Run Outcome\n\n`
  for (let i = 0; i < runs.length; i++) {
    const catName = getRunCategoryName(runs[i].child_id)
    md += `**#${i + 1}** [${catName}]: ${runs[i].outcome_summary || '—'}\n\n`
  }

  md += `## Statistics\n\n`
  md += `| Metric | Mean | Std | Min | Max |\n`
  md += `|--------|------|-----|-----|-----|\n`
  for (const key of ['total_actions', 'total_posts', 'total_likes', 'total_comments', 'total_reposts']) {
    const s = agg[key]
    if (s) md += `| ${formatStatKey(key)} | ${s.mean} | ±${s.std} | ${s.min} | ${s.max} |\n`
  }

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `monte-carlo-report-${props.groupId}.md`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.mc-results-panel { padding: 0 0 40px; }

.results-header { margin-bottom: 20px; }
.back-btn { background: none; border: none; color: #666; font-size: 12px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.back-btn:hover { color: #333; }
.results-title { font-size: 18px; font-weight: 700; font-family: 'Space Grotesk', sans-serif; margin: 0; }

.section-title { font-size: 14px; font-weight: 600; margin: 0 0 12px; color: #333; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* Key Insight Banner */
.key-insight-banner {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 16px 20px;
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  border-radius: 12px;
  margin-bottom: 24px;
  color: #fff;
}
.insight-icon { flex-shrink: 0; margin-top: 2px; opacity: 0.7; }
.insight-content { display: flex; flex-direction: column; gap: 4px; }
.insight-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.6; }
.insight-text { font-size: 15px; font-weight: 600; line-height: 1.4; }

/* Overview Row */
.overview-row {
  display: flex;
  gap: 24px;
  align-items: center;
  margin-bottom: 28px;
}
.convergence-gauge { flex-shrink: 0; text-align: center; }
.gauge-circle { position: relative; width: 100px; height: 100px; }
.gauge-circle svg { width: 100%; height: 100%; }
.gauge-value {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  display: flex; align-items: baseline; gap: 1px;
}
.gauge-num { font-size: 22px; font-weight: 700; color: #333; }
.gauge-unit { font-size: 11px; color: #999; }
.gauge-label { font-size: 11px; color: #999; margin-top: 4px; display: block; }

.stats-compact { flex: 1; display: flex; flex-wrap: wrap; gap: 8px; }
.stat-pill {
  padding: 8px 14px;
  background: #F8F9FA;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  display: flex; flex-direction: column; gap: 2px;
}
.pill-key { font-size: 10px; color: #999; text-transform: uppercase; letter-spacing: 0.3px; }
.pill-val { font-size: 16px; font-weight: 700; color: #333; }
.pill-std { font-size: 11px; color: #999; font-weight: 400; margin-left: 2px; }

/* Category Cards */
.categories-section { margin-bottom: 28px; }
.category-cards { display: flex; flex-direction: column; gap: 10px; }
.category-card {
  padding: 14px 18px;
  background: #fff;
  border: 1px solid #EAEAEA;
  border-left: 4px solid;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.category-card:hover { background: #FAFAFA; }
.category-card.active { background: #F5F7FA; border-color: #DDD; }
.cat-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.cat-color { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.cat-name { font-size: 14px; font-weight: 600; flex: 1; }
.cat-pct { font-size: 12px; color: #666; }
.cat-desc { font-size: 13px; color: #666; margin: 0; line-height: 1.4; }
.cat-summary { font-size: 13px; color: #333; margin: 8px 0 0; line-height: 1.5; padding-top: 8px; border-top: 1px dashed #EAEAEA; }

/* Run Outcomes */
.run-outcomes-section { margin-bottom: 28px; }
.outcomes-list { display: flex; flex-direction: column; gap: 6px; }
.outcome-row {
  display: flex; gap: 10px; align-items: center;
  padding: 10px 14px;
  background: #FAFAFA;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  transition: all 0.15s;
}
.outcome-row.clickable { cursor: pointer; }
.outcome-row.clickable:hover { background: #F0F4FF; border-color: #C5D5F0; }
.outcome-index { flex-shrink: 0; font-size: 12px; font-weight: 600; color: #999; min-width: 28px; }
.outcome-cat-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.outcome-text { flex: 1; font-size: 13px; color: #333; line-height: 1.4; }
.outcome-arrow { color: #CCC; font-size: 14px; flex-shrink: 0; transition: color 0.15s; }
.outcome-row:hover .outcome-arrow { color: #666; }

/* Distribution Charts */
.distributions-section { margin-bottom: 28px; }
.charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }
.chart-wrapper { padding: 12px; background: #FAFAFA; border: 1px solid #EAEAEA; border-radius: 8px; }

/* Actions */
.action-btn { padding: 10px 20px; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; transition: all 0.2s; }
.action-btn.primary { background: #333; color: #fff; }
.action-btn.primary:hover { background: #000; }
.action-btn.full-width { width: 100%; }
.report-section { margin-top: 24px; }
.no-analysis { text-align: center; padding: 60px 20px; color: #999; }
</style>
