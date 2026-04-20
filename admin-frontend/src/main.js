/****
 @File        : main.js
 @Author      : taichilei
 @Date        : 2025-04-01
 @Description : This is the main file of the project.
 @Project     : admin-frontend
 @Version     : 1.0.0
 @Copyright   : Copyright © 2025. All rights reserved.
 ****/

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import './assets/styles/global.css'
import i18n from './i18n'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

// ----------------- 恢复用户信息 -----------------
const savedUser = localStorage.getItem('user_info')
if (savedUser) {
  const userData = JSON.parse(savedUser)
  userStore.setUser(userData, userData.token)
}
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

// ----------------- 创建并挂载 Vue 应用 -----------------
const app = createApp(App)

app.use(i18n).use(router).use(pinia).use(ElementPlus)

app.mount('#app')
