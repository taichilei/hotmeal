import {defineConfig} from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        uni(),
    ],
    server: {
        port: 8080,
        host: '0.0.0.0',
    },
    css: {
        preprocessorOptions: {
            scss: {
                additionalData: `@import "uview-plus/theme.scss";`
            }
        }
    },
    resolve: {
        alias: {
            'uview-plus': 'uview-plus'
        }
    }
})
