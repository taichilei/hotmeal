/****
 * @file            vite.config.js
 * @description     Vite 构建工具配置文件，定义项目如何编译、开发服务器如何启动
 * @author          taichilei
 * @date            2025-04-23
 * @version         1.0.0
 */

import { defineConfig } from 'vite'
// 启用 Vue 单文件组件 (.vue) 编译支持
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig(() => ({
  // 插件配置
  plugins: [
    vue() // 处理 .vue 单文件组件
  ],
  // 模块解析配置
  resolve: {
    // 路径别名配置 - 简化 import 路径
    alias: {
      '@': resolve(__dirname, 'src'), // @ 代表 src 目录，可写 import xx from '@/components/xxx'
    },
  },
  // 开发服务器配置 (npm run dev 时生效)
  server: {
    host: '0.0.0.0',      // 监听所有地址，允许局域网访问
    port: 5000,           // 开发服务器端口号
    open: true,           // 启动后自动在浏览器打开项目
    // API 代理配置 - 解决开发环境跨域问题
    proxy: {
      // 所有以 /api 开头的请求都会被代理到后端
      '/api': {
        target: 'https://127.0.0.1:5000',  // 后端服务地址
        secure: false,                      // 忽略 HTTPS 自签名证书验证（开发调试用）
        changeOrigin: true,                 // 修改请求头中的 Origin 为目标地址
        rewrite: (path) => path.replace(/^\/api/, '/api'), // 路径重写（这里保持原路径）
      },
    },
  },
}))
