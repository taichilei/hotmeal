import { createI18n } from 'vue-i18n'
import zhCN from '../locale/zh-CN.json'
import en from '../locale/en.json'

const messages = {
  'zh-CN': zhCN,
  'en': en
}

// 获取系统语言
const getSystemLanguage = () => {
  try {
    const systemInfo = uni.getSystemInfoSync()
    return systemInfo.language || 'zh-CN'
  } catch (e) {
    return 'zh-CN'
  }
}

const i18n = createI18n({
  legacy: false, // 使用 Composition API 模式
  globalInjection: true, // 全局注入 $t 等方法
  locale: uni.getStorageSync('language') || getSystemLanguage(), // 默认语言
  fallbackLocale: 'zh-CN', // 降级语言
  messages
})

export default i18n
