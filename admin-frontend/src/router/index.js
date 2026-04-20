/**
 @File        : router/index.js
 @Author      : taichilei
 @Date        : 2025-04-13
 @Description : router configuration
 **/
import { createRouter, createWebHistory } from 'vue-router'

import adminRoutes from './admin'
import staffRoutes from './staff'
import publicRoutes from './public'

const routes = [...publicRoutes, ...adminRoutes, ...staffRoutes]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role') // 可用登录后保存的用户角色

  // 如果未登录且不是访问登录页，强制跳转登录
  if (!token && to.path !== '/login') {
    return next('/login')
  }

  // 登录后访问 / 或 /home，根据角色自动跳转
  if (to.path === '/' || to.path === '/home') {
    if (role === 'admin') {
      return next('/admin/dashboard')
    } else if (role === 'staff') {
      return next('/staff/dashboard')
    } else {
      return next('/login')
    }
  }

  next()
})

export default router
