<!--
@File        : RingChart.vue
@Author      : taichilei
@Date        : 2025-04-22
@Description : 基于 ECharts 的可复用环图/圆环图组件，具有苹果风格圆角与浅色背景
-->
<template>
  <div class="ring-card">
    <!-- 环图容器 -->
    <div ref="chartRef" :style="{ width: '100%', height: height + 'px' }"></div>
  </div>
</template>

<script setup>
  import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
  import * as echarts from 'echarts'

  // props:
  // - options: 完整的 ECharts 配置对象，用于定制环图数据与样式
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

  // 初始化环图
  onMounted(() => {
    if (chartRef.value) {
      chartInstance = echarts.init(chartRef.value)
      chartInstance.setOption(props.options)
      window.addEventListener('resize', resizeChart)
    }
  })

  // 监听配置变更，实时更新
  watch(
    () => props.options,
    (newOpt) => {
      if (chartInstance) {
        chartInstance.setOption(newOpt, true)
      }
    },
    { deep: true },
  )

  // 适应容器或窗口大小变化
  function resizeChart() {
    if (chartInstance) {
      chartInstance.resize()
    }
  }

  // 组件卸载前清理
  onBeforeUnmount(() => {
    window.removeEventListener('resize', resizeChart)
    if (chartInstance) {
      chartInstance.dispose()
      chartInstance = null
    }
  })
</script>

<style scoped>
  .ring-card {
    background-color: #f2f2f7;
    border-radius: 16px;
    padding: 16px;
  }
</style>
