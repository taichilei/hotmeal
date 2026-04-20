<!--
@File        : AdminLoginForm.vue
@Author      : taichilei
@Date        : 2025-04-18
@Description : 
-->
<template>
  <el-form :model="form" @submit.prevent="onSubmit">
    <el-form-item label="账号">
      <el-input v-model="form.account" />
    </el-form-item>
    <el-form-item label="密码">
      <el-input type="password" v-model="form.password" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="onSubmit">登录</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
  import { ref } from 'vue'
  const emit = defineEmits(['login'])

  const form = ref({ account: '', password: '' })

  const onSubmit = () => {
    emit('login', form.value)
  }
</script>
