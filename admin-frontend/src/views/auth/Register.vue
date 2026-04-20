<!--
@File        : Register.vue
@Author      : taichilei
@Date        : 2025-04-14
@Description :
-->
<template>
  <div class="register-page">
    <NavigationBar role="admin" />
    <img :src="src" alt="背景图片" class="background-image" draggable="false" />
    <div class="register-main">
      <div class="register-container">
        <h2 class="title">{{ t('auth.register.title') }}</h2>
        <el-form label-position="left" label-width="80px">
          <el-form-item :label="t('auth.register.role')">
            <el-select v-model="role" placeholder="请选择角色" size="large">
              <el-option
                v-for="item in roleOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('auth.register.account')">
            <el-input v-model="account" resize="both" size="large"></el-input>
          </el-form-item>
          <el-form-item :label="t('auth.register.password')">
            <el-input v-model="password" resize="both" size="large"></el-input>
          </el-form-item>
          <el-form-item :label="t('auth.register.confirmPassword')">
            <el-input v-model="confirmPassword" resize="both" size="large"></el-input>
          </el-form-item>
          <el-form-item>
            <el-button class="register-button" type="primary" @click="onSubmit">
              {{ t('auth.register.registerButton') }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
    <Footer />
  </div>
</template>

<script setup>
  import { ref } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { ElMessage } from 'element-plus'
  import { addUser } from '@/api/user'
  import router from '@/router'
  import NavigationBar from '@/components/common/NavigationBar.vue'
  import Footer from '@/components/common/Footer.vue'

  const { t } = useI18n()

  const src = new URL('../assets/3.webp', import.meta.url).href

  const account = ref('')
  const password = ref('')
  const confirmPassword = ref('')
  const role = ref('USER')
  const roleOptions = [
    { label: '用户', value: 'USER' },
    { label: '管理员', value: 'ADMIN' },
  ]

  function onSubmit() {
    /**
     * 校验表单
     *  1. 账号不能为空
     *  2. 密码不能为空
     *  3. 两次密码输入一致
     */
    if (!account.value || !password.value) {
      ElMessage.warning(t('auth.register.incompleteForm'))
      return
    }
    if (password.value !== confirmPassword.value) {
      ElMessage.warning(t('auth.register.passwordMismatch'))
      return
    }

    sessionStorage.setItem('registerAccount', account.value)
    addUser({
      account: account.value,
      role: role.value,
      password: password.value,
    })
      .then(() => {
        ElMessage.success(t('auth.register.success'))
        router.push('/login')
      })
      .catch(() => {
        ElMessage.error(t('auth.register.failed'))
      })
  }
</script>

<style>
  * {
    font-family: 'Maple Mono', monospace;
  }

  .register-page {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    position: relative;
  }

  .register-main {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    z-index: 1;
    padding: 60px 0; /* 新增 */
  }

  .background-image {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    z-index: -1;
  }

  .register-container {
    background-color: #81d8d0;
    padding: 35px;
    border-radius: 15px;
    box-sizing: border-box;
    min-width: 320px;
    min-height: 300px; /* 新增 */
  }

  .register-button {
    margin-top: 10%;
    margin-left: 20%;
  }

  .title {
    text-align: center;
    font-size: 24px;
    margin-bottom: 20px;
  }
</style>
