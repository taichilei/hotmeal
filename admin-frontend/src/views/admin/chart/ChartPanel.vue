<!--
@File        : ChartPanel.vue
@Author      : taichilei
@Date        : 2025-04-22
@Description : 
-->
<template>
  <div class="chart-grid">
    <div class="chart-item">
      <PieChart :options="pieOptions" :height="300" />
    </div>
    <div class="chart-item">
      <BarChart :options="barOptions" :height="300" />
    </div>
    <div class="chart-item">
      <BaseChart :options="baseOptions" :height="300" />
    </div>
    <div class="chart-item">
      <LineChart :options="lineOptions" :height="300" />
    </div>
    <div class="chart-item">
      <RingChart :options="ringOptions" :height="300" />
    </div>
  </div>
</template>

<script setup>
  import { reactive } from 'vue'
  import PieChart from '@/components/chart/PieChart.vue'
  import BarChart from '@/components/chart/BarChart.vue'
  import LineChart from '@/components/chart/LineChart.vue'
  import BaseChart from '@/components/chart/BaseChart.vue'
  import RingChart from '@/components/chart/RingChart.vue'

  // 示例用饼图配置
  const pieOptions = reactive({
    title: {
      text: '市场占比示例',
      left: 'center',
      top: '5%', // 将标题上移至图表上方
    },
    tooltip: { trigger: 'item' },
    legend: {
      orient: 'vertical',
      right: '10%', // 靠右
      bottom: '10%', // 靠下
      textStyle: {
        color: '#333',
      },
    },
    series: [
      {
        name: '访问来源',
        type: 'pie',
        radius: '50%',
        center: ['40%', '45%'], // 向上移动一点
        data: [
          { value: 335, name: '直接访问' },
          { value: 310, name: '邮件营销' },
          { value: 234, name: '联盟广告' },
          { value: 135, name: '视频广告' },
          { value: 1548, name: '搜索引擎' },
        ],
      },
    ],
  })

  // 示例用柱状图配置
  const barOptions = reactive({
    title: {
      text: '销售额统计',
      left: 'center',
      top: '5%', // 将标题上移至图表上方
    },
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['销售额'],
      bottom: '10%', // 靠下
      textStyle: {
        color: '#333',
      },
    },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      axisLabel: {
        color: '#333',
      },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#333',
      },
    },
    series: [
      {
        name: '销售额',
        type: 'bar',
        data: [1000, 2000, 3000, 4000, 5000, 6000, 7000],
      },
    ],
  })

  // 示例用折线图配置
  const lineOptions = reactive({
    title: {
      text: '销售额趋势图',
      left: 'center',
      top: '5%', // 将标题上移至图表上方
    },
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['销售额'],
      bottom: '10%', // 靠下
      textStyle: {
        color: '#333',
      },
    },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      axisLabel: {
        color: '#333',
      },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#333',
      },
    },
    series: [
      {
        name: '销售额',
        type: 'line',
        data: [1000, 2000, 3000, 4000, 5000, 6000, 7000],
      },
    ],
  })

  // 示例用基础图表配置
  const baseOptions = reactive({
    title: {
      text: '基础图表示例',
      left: 'center',
      top: '5%', // 将标题上移至图表上方
    },
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['销售额'],
      bottom: '10%', // 靠下
      textStyle: {
        color: '#333',
      },
    },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      axisLabel: {
        color: '#333',
      },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#333',
      },
    },
    series: [
      {
        name: '销售额',
        type: 'bar',
        data: [1000, 2000, 3000, 4000, 5000, 6000, 7000],
      },
    ],
  })

  // 示例用环形图配置
  const ringOptions = reactive({
    title: {
      text: '环形图示例',
      left: 'center',
      top: '5%', // 将标题上移至图表上方
    },
    tooltip: { trigger: 'item' },
    legend: {
      orient: 'vertical',
      right: '10%', // 靠右
      bottom: '10%', // 靠下
      textStyle: {
        color: '#333',
      },
    },
    series: [
      {
        name: '访问来源',
        type: 'pie',
        radius: ['0', '50%'],
        center: ['50%', '50%'],
        data: [
          { value: 335, name: '直接访问' },
          { value: 310, name: '邮件营销' },
          { value: 234, name: '联盟广告' },
          { value: 135, name: '视频广告' },
          { value: 1548, name: '搜索引擎' },
        ],
        itemStyle: {
          emphasis: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      },
    ],
  })
</script>

<style scoped>
  .chart-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
  .chart-item {
    width: 100%;
  }
</style>
