/**
 * @file         src/main.js
 * @author       taichilei
 * @date         2025-04-30
 * @description
 */

import {createSSRApp} from "vue";
import App from "./App.vue";
import uviewPlus from 'uview-plus'
import {createPinia} from 'pinia'
// 引入 pinia-plugin-persistedstate 插件,需要自定义存储方式
import {createPersistedState} from 'pinia-plugin-persistedstate'
import i18n from './i18n'


export function createApp() {
    const app = createSSRApp(App);
    const pinia = createPinia()

    // 自定义存储方式，兼容 uni-app（替代默认 localStorage）
    const customStorage = {
        getItem: (key) => uni.getStorageSync(key),
        setItem: (key, value) => uni.setStorageSync(key, value),
    }
    // 注册 pinia-plugin-persistedstate 插件
    pinia.use(createPersistedState({storage: customStorage}))
    // 注册 pinia
    app.use(pinia)
    // 挂载 uview-plus 插件
    app.use(uviewPlus)
    // 挂载国际化插件
    app.use(i18n)
    return {
        app,
    };
}
