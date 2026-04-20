<!--
@File        : BarChart.vue
@Author      : taichilei
@Date        : 2025-04-22
@Description : 基于 ECharts 的可复用柱状图组件
-->
<template>
  <!-- iPhone 风格浅色卡片 -->
  <div class="chart-card">
    <!-- 图表容器 -->
    <div ref="chartRef" :style="{ width: '100%', height: height + 'px' }"></div>
  </div>
</template>

<script setup>
  import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
  import * as echarts from 'echarts'

  // props:
  // - options: 完整的 ECharts 配置对象，用于自定义坐标轴、系列等配置
  // - height:  图表容器高度（单位 px），默认 300
  const props = defineProps({
    options: {
      type: Object,
      default: () => ({}),
    },
    height: {
      type: Number,
      default: 300,
    },
  })

  const chartRef = ref(null)
  let chartInstance = null

  // 初始化图表
  onMounted(() => {
    if (chartRef.value) {
      chartInstance = echarts.init(chartRef.value)
      chartInstance.setOption(props.options)
      window.addEventListener('resize', resizeChart)
    }
  })

  // 监听配置变更，更新图表
  watch(
    () => props.options,
    (newOpt) => {
      if (chartInstance) {
        chartInstance.setOption(newOpt, true)
      }
    },
    { deep: true },
  )

  // 自适应窗口变化
  function resizeChart() {
    if (chartInstance) {
      chartInstance.resize()
    }
  }

  // 销毁时清理
  onBeforeUnmount(() => {
    window.removeEventListener('resize', resizeChart)
    if (chartInstance) {
      chartInstance.dispose()
      chartInstance = null
    }
  })
</script>

<style scoped>
  .chart-card {
    background-color: #f2f2f7; /* iOS 系统浅色背景 */
    border-radius: 16px; /* 接近 iPhone 圆角 */
    padding: 16px;
  }
  /* 可根据项目需要在此添加额外样式 */
</style>
