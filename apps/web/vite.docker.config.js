import { defineConfig } from 'vite'

export default defineConfig({
  build: {
    target: 'es2020',
    rollupOptions: {
      external: ['@rollup/rollup-linux-*'] 
    }
  }
}) 