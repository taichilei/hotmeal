<!--
@File        : Profile.vue
@Author      : taichilei
@Date        : 2025-05-03
@Description : This is the profile page.
-->
<template>
  <component :is="layoutComponent">
    <div class="profile-container">
      <h2 style="margin-bottom: 20px">个人中心</h2>
      <el-form ref="formRef" :model="form" label-width="100px" style="max-width: 600px">
        <el-form-item label="账号">
          <el-input v-model="form.account" disabled />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone_number" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="头像 URL">
          <el-input v-model="form.avatar_url" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" placeholder="请选择角色">
            <el-option label="管理员" value="ADMIN" />
            <el-option label="员工" value="STAFF" />
            <el-option label="用户" value="USER" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit">保存修改</el-button>
        </el-form-item>
      </el-form>
    </div>
  </component>
</template>

<script setup>
  import { computed, onMounted, ref } from 'vue'
  import AdminLayout from '@/layouts/admin/AdminLayout.vue'
  import StaffLayout from '@/layouts/staff/StaffLayout.vue'
  import { useUserStore } from '@/stores/userStore'
  import { updateUserInfo, getUserInfo } from '@/api/user'
  import { ElMessage } from 'element-plus'

  const formRef = ref()
  const userStore = useUserStore()

  const form = ref({
    account: '',
    username: '',
    phone_number: '',
    email: '',
    avatar_url: '',
    role: '',
  })

  // 初始化用户数据
  onMounted(async () => {
    // 初始从 store 赋值
    form.value = {
      account: userStore.account,
      username: userStore.username,
      phone_number: userStore.phone_number,
      email: userStore.email,
      avatar_url: userStore.avatar_url,
      role: userStore.role,
    }

    // 后台获取最新数据并覆盖
    try {
      const res = await getUserInfo()
      if (res?.data?.error_code === 0 && res?.data?.data) {
        const userData = res.data.data
        Object.assign(userStore, userData)
        Object.assign(form.value, userData)
      } else {
        console.warn('获取用户信息失败', res)
      }
    } catch (e) {
      console.error('获取用户信息异常', e)
    }
  })

  const layoutComponent = computed(() => {
    const role = userStore.role
    if (role === 'ADMIN') return AdminLayout
    if (role === 'STAFF') return StaffLayout
    return AdminLayout // 兜底
  })

  async function handleSubmit() {
    /**
     * 表单校验 这里重点检查
     */
    try {
      const res = await updateUserInfo(form.value)
      console.log('更新响应：', res)

      const errorCode = res?.data?.error_code
      const message = res?.data?.message || '未知返回信息'

      if (errorCode === 0) {
        ElMessage({
          message: '用户信息更新成功',
          type: 'success',
          showClose: true,
          grouping: true,
          duration: 3000,
          offset: 80,
          position: 'top-right',
        })
        userStore.username = form.value.username
        userStore.phone_number = form.value.phone_number
        userStore.email = form.value.email
        userStore.avatar_url = form.value.avatar_url
      } else {
        console.warn('后端返回非0错误码：', errorCode, message)
        ElMessage({
          message: `更新失败：${message}`,
          type: 'error',
          showClose: true,
          offset: 80,
          position: 'top-right',
        })
      }
    } catch (err) {
      console.error('更新用户信息请求异常：', err)
      ElMessage({
        message: '请求失败，请稍后重试',
        type: 'error',
        showClose: true,
        offset: 80,
        position: 'top-right',
      })
    }
  }
</script>

<style scoped></style>
