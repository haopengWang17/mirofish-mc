<template>
  <div class="distribution-chart" ref="chartContainer"></div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  data: {
    type: Array,    // Array of numbers
    default: () => [],
  },
  label: {
    type: String,
    default: '',
  },
  color: {
    type: String,
    default: '#333',
  },
  width: {
    type: Number,
    default: 400,
  },
  height: {
    type: Number,
    default: 200,
  },
})

const chartContainer = ref(null)

const renderChart = () => {
  if (!chartContainer.value || !props.data.length) return

  // 清除旧图
  d3.select(chartContainer.value).selectAll('*').remove()

  const margin = { top: 20, right: 20, bottom: 35, left: 45 }
  const w = props.width - margin.left - margin.right
  const h = props.height - margin.top - margin.bottom

  const svg = d3.select(chartContainer.value)
    .append('svg')
    .attr('width', props.width)
    .attr('height', props.height)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  const values = props.data

  // 计算 bin
  const x = d3.scaleLinear()
    .domain([d3.min(values) * 0.9, d3.max(values) * 1.1])
    .range([0, w])

  const bins = d3.bin()
    .domain(x.domain())
    .thresholds(Math.min(Math.ceil(Math.sqrt(values.length)), 20))
    (values)

  const y = d3.scaleLinear()
    .domain([0, d3.max(bins, d => d.length)])
    .nice()
    .range([h, 0])

  // 绘制柱子
  svg.selectAll('.bar')
    .data(bins)
    .join('rect')
    .attr('class', 'bar')
    .attr('x', d => x(d.x0) + 1)
    .attr('y', d => y(d.length))
    .attr('width', d => Math.max(0, x(d.x1) - x(d.x0) - 2))
    .attr('height', d => h - y(d.length))
    .attr('fill', props.color)
    .attr('opacity', 0.8)
    .attr('rx', 2)

  // 均值线
  const mean = d3.mean(values)
  svg.append('line')
    .attr('x1', x(mean))
    .attr('x2', x(mean))
    .attr('y1', 0)
    .attr('y2', h)
    .attr('stroke', '#F44336')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '4,3')

  svg.append('text')
    .attr('x', x(mean) + 4)
    .attr('y', 12)
    .attr('fill', '#F44336')
    .attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .text(`μ=${mean.toFixed(1)}`)

  // X 轴
  svg.append('g')
    .attr('transform', `translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(6))
    .selectAll('text')
    .attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace')

  // Y 轴
  svg.append('g')
    .call(d3.axisLeft(y).ticks(4))
    .selectAll('text')
    .attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace')

  // 标签
  if (props.label) {
    svg.append('text')
      .attr('x', w / 2)
      .attr('y', h + 30)
      .attr('text-anchor', 'middle')
      .attr('fill', '#999')
      .attr('font-size', '11px')
      .text(props.label)
  }
}

watch(() => props.data, renderChart, { deep: true })
onMounted(renderChart)
onBeforeUnmount(() => {
  if (chartContainer.value) d3.select(chartContainer.value).selectAll('*').remove()
})
</script>

<style scoped>
.distribution-chart {
  display: flex;
  justify-content: center;
}

.distribution-chart :deep(svg) {
  overflow: visible;
}

.distribution-chart :deep(.domain) {
  stroke: #DDD;
}

.distribution-chart :deep(.tick line) {
  stroke: #EEE;
}
</style>
