<template>
  <div v-if="visible" class="mc-setup-overlay" @click.self="$emit('close')">
    <div class="mc-setup-modal">
      <div class="modal-header">
        <h3>{{ $t('monteCarlo.title') }}</h3>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- 预设选择 -->
        <div class="presets-row">
          <div
            v-for="preset in presets"
            :key="preset.key"
            class="preset-card"
            :class="{ active: activePreset === preset.key }"
            @click="applyPreset(preset)"
          >
            <span class="preset-icon">{{ preset.icon }}</span>
            <span class="preset-name">{{ preset.name }}</span>
            <span class="preset-desc">{{ preset.runs }} {{ $t('monteCarlo.runsUnit') }}</span>
          </div>
        </div>

        <!-- 运行次数 -->
        <div class="config-row">
          <label class="config-label">{{ $t('monteCarlo.numRuns') }}</label>
          <div class="config-control">
            <input
              type="range"
              v-model.number="numRuns"
              min="2"
              max="100"
              step="1"
              class="minimal-slider"
              :style="{ '--percent': ((numRuns - 2) / 98) * 100 + '%' }"
              @input="activePreset = 'custom'"
            />
            <div class="range-display">
              <input
                type="number"
                v-model.number="numRuns"
                min="2"
                max="100"
                class="num-input"
              />
              <span class="num-unit">{{ $t('monteCarlo.runsUnit') }}</span>
            </div>
          </div>
        </div>

        <!-- 最大并发 -->
        <div class="config-row">
          <label class="config-label">{{ $t('monteCarlo.maxConcurrency') }}</label>
          <div class="config-control">
            <input
              type="range"
              v-model.number="maxConcurrency"
              min="1"
              max="10"
              step="1"
              class="minimal-slider"
              :style="{ '--percent': ((maxConcurrency - 1) / 9) * 100 + '%' }"
            />
            <div class="range-display">
              <input
                type="number"
                v-model.number="maxConcurrency"
                min="1"
                max="10"
                class="num-input"
              />
              <span class="num-unit">{{ $t('monteCarlo.concurrencyUnit') }}</span>
            </div>
          </div>
          <p class="config-hint">{{ $t('monteCarlo.concurrencyHint') }}</p>
        </div>

        <!-- 分类标准 -->
        <div class="config-row">
          <label class="config-label">{{ $t('monteCarlo.classificationCriteria') }}</label>
          <textarea
            v-model="classificationCriteria"
            :placeholder="$t('monteCarlo.criteriaPlaceholder')"
            class="criteria-input"
            rows="3"
          ></textarea>
          <p class="config-hint">{{ $t('monteCarlo.criteriaHint') }}</p>
        </div>
      </div>

      <div class="modal-footer">
        <button class="action-btn secondary" @click="$emit('close')">
          {{ $t('common.cancel') }}
        </button>
        <button class="action-btn primary" @click="handleConfirm">
          {{ $t('monteCarlo.startMonteCarlo') }} →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({ visible: Boolean })
const emit = defineEmits(['close', 'confirm'])

const numRuns = ref(10)
const maxConcurrency = ref(2)
const classificationCriteria = ref('')
const activePreset = ref('standard')

const presets = [
  { key: 'quick', icon: '⚡', name: t('monteCarlo.presetQuick'), runs: 3, concurrency: 2 },
  { key: 'standard', icon: '⊙', name: t('monteCarlo.presetStandard'), runs: 10, concurrency: 2 },
  { key: 'thorough', icon: '◎', name: t('monteCarlo.presetThorough'), runs: 30, concurrency: 3 },
]

const applyPreset = (preset) => {
  activePreset.value = preset.key
  numRuns.value = preset.runs
  maxConcurrency.value = preset.concurrency
}

const handleConfirm = () => {
  emit('confirm', {
    num_runs: numRuns.value,
    max_concurrency: maxConcurrency.value,
    classification_criteria: classificationCriteria.value,
  })
}
</script>

<style scoped>
.mc-setup-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0, 0, 0, 0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; backdrop-filter: blur(2px);
}
.mc-setup-modal {
  background: #fff; border-radius: 14px; width: 540px; max-width: 92vw;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.18);
}

.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px; border-bottom: 1px solid #EAEAEA;
}
.modal-header h3 { font-size: 16px; font-weight: 700; margin: 0; font-family: 'Space Grotesk', sans-serif; }
.close-btn { background: none; border: none; font-size: 22px; cursor: pointer; color: #999; padding: 4px 8px; }

.modal-body { padding: 24px; }

/* Presets */
.presets-row { display: flex; gap: 10px; margin-bottom: 24px; }
.preset-card {
  flex: 1; text-align: center; padding: 14px 10px;
  border: 2px solid #EAEAEA; border-radius: 10px;
  cursor: pointer; transition: all 0.15s;
  display: flex; flex-direction: column; gap: 4px;
}
.preset-card:hover { border-color: #CCC; }
.preset-card.active { border-color: #333; background: #F8F9FA; }
.preset-icon { font-size: 20px; }
.preset-name { font-size: 13px; font-weight: 600; color: #333; }
.preset-desc { font-size: 11px; color: #999; font-family: 'JetBrains Mono', monospace; }

.config-row { margin-bottom: 20px; }
.config-label { display: block; font-size: 13px; font-weight: 600; color: #333; margin-bottom: 8px; }
.config-control { display: flex; align-items: center; gap: 16px; }

.minimal-slider {
  flex: 1; -webkit-appearance: none; height: 4px; border-radius: 2px;
  background: linear-gradient(to right, #333 0%, #333 var(--percent, 50%), #EAEAEA var(--percent, 50%), #EAEAEA 100%);
  outline: none;
}
.minimal-slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%;
  background: #333; cursor: pointer;
}

.range-display { display: flex; align-items: center; gap: 4px; }
.num-input {
  width: 56px; padding: 4px 8px; border: 1px solid #DDD; border-radius: 6px;
  font-size: 14px; font-family: 'JetBrains Mono', monospace; text-align: center;
}
.num-unit { font-size: 12px; color: #999; }
.config-hint { font-size: 11px; color: #999; margin-top: 6px; }

.criteria-input {
  width: 100%; padding: 10px 12px; border: 1px solid #DDD; border-radius: 8px;
  font-size: 13px; font-family: 'Space Grotesk', sans-serif;
  resize: vertical; outline: none; transition: border-color 0.2s; box-sizing: border-box;
}
.criteria-input:focus { border-color: #333; }

.modal-footer {
  display: flex; justify-content: flex-end; gap: 12px;
  padding: 16px 24px; border-top: 1px solid #EAEAEA;
}
.action-btn {
  padding: 10px 22px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: none; transition: all 0.2s;
}
.action-btn.primary { background: #333; color: #fff; }
.action-btn.primary:hover { background: #000; }
.action-btn.secondary { background: #F5F5F5; color: #333; border: 1px solid #DDD; }
.action-btn.secondary:hover { background: #EAEAEA; }
</style>
