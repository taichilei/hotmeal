<!--
@File        : TopDishes.vue
@Author      : taichilei
@Date        : 2025-05-05
@Description : 热门菜品排行榜柱状图
-->
<template>
  <div ref="chartRef" class="chart"></div>
</template>

<script setup>
  import * as echarts from 'echarts'
  import { ref, onMounted, nextTick } from 'vue'

  const chartRef = ref(null)

  const chartOption = {
    title: {
      text: '热销菜品 Top 5',
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      boundaryGap: [0, 0.01],
    },
    yAxis: {
      type: 'category',
      data: ['宫保鸡丁', '鱼香肉丝', '番茄炒蛋', '红烧肉', '酸辣土豆丝'],
    },
    series: [
      {
        name: '销量',
        type: 'bar',
        data: [980, 870, 750, 620, 540],
        itemStyle: {
          color: '#73C0DE',
        },
      },
    ],
  }

  onMounted(() => {
    nextTick(() => {
      const chart = echarts.init(chartRef.value)
      chart.setOption(chartOption)
    })
  })
</script>

<style scoped>
  .chart {
    width: 100%;
    height: 400px;
  }
</style>
