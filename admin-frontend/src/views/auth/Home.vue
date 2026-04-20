<!--
@File        : Home.vue
@Author      : taichilei
@Date        : 2025-04-18
@Description : 
-->

<template>
  <div class="home-container">
    <h2>欢迎回来，{{ user?.name || '游客' }}</h2>
    <p v-if="user?.role === 'admin'">您可以管理订单、用户和菜品。</p>
    <p v-else-if="user?.role === 'staff'">您可以处理派单和出餐。</p>
    <p v-else>欢迎使用点餐系统！</p>
  </div>
</template>

<script setup>
  import { computed } from 'vue'

  const store = useStore()
  const user = computed(() => store.state.user)
</script>
