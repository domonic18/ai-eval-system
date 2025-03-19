import './assets/main.css'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import api from './utils/api'

// 启动应用前，确保尝试恢复认证状态
store.dispatch('auth/autoLogin')

const app = createApp(App)

// 提供给所有组件
app.provide('api', api)

// 兼容选项式API
app.config.globalProperties.$api = api

app.use(router)
app.use(store)
app.use(ElementPlus)
app.mount('#app')
