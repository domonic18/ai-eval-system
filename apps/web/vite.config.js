import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  optimizeDeps: {
    include: [
      '@vueform/multiselect'
    ]
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  build: {
    // 添加构建配置
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    // 禁用本地依赖优化
    commonjsOptions: {
      include: []
    }
  },
  server: {
    host: '0.0.0.0', 
    port: 5173,
    watch: {
      usePolling: true,  // Docker中监听文件变化
      interval: 1000,    // 检查间隔
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/api/, '/api')
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ws/, '')
      }
    }
  }
})
