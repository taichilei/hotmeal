<!--
@File        : Menu.vue
@Author      : taichilei
@Date        : 2025-04-17
@Description : 
-->
<template>
  <div class="menu-page">
    <div class="menu-container">
      <router-link to="/admin/login">{{ t('admin.login') }}</router-link>
      <router-link to="/staff/login">{{ t('staff.login') }}</router-link>
      <router-link to="/user/login">{{ t('user.login') }}</router-link>
    </div>
  </div>
</template>

<script setup>
  import { useI18n } from 'vue-i18n'

  const { t } = useI18n()
</script>

<style>
  .menu-page {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
  }
  .menu-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }
</style>
