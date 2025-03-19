import { createStore } from 'vuex'
import auth from './modules/auth'

const store = createStore({
  modules: {
    auth
  }
})

// 应用启动时尝试恢复会话
store.dispatch('auth/autoLogin')

export default store