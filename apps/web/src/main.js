import './assets/main.css'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import api from './utils/api'

const app = createApp(App)

// 全局API客户端
app.config.globalProperties.$api = api
// 替换全局axios，确保使用我们的拦截器
app.config.globalProperties.$http = api

app.use(router)
app.use(store)
app.use(ElementPlus)
app.mount('#app')
