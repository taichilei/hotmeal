/**
 * @file         src/config.js
 * @author       taichilei
 * @date         2025-04-30
 * @description
 */

// 项目配置文件

// 是否为开发环境
export const isDev = process.env.NODE_ENV === 'development';

// 后端 API 基础地址
export const BASE_URL = isDev
    ? 'http://127.0.0.1:5001/api/v1'
    : 'https://your-production-api.com/api/v1';

// 项目标题
export const APP_TITLE = 'HotMeal 点餐系统';