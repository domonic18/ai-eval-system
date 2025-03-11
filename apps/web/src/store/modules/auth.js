import http from '@/utils/axios'  // 导入配置的axios实例

// 初始状态
const state = {
  token: null,
  user: null,
  loading: false,
  error: null
}

// getter
const getters = {
  isLoggedIn: state => !!state.token,
  username: state => state.user?.username || '未知用户',
  user: state => state.user,
  isAdmin: state => state.user?.is_admin || false
}

// 突变
const mutations = {
  setToken(state, token) {
    state.token = token
    // 保存token到localStorage
    if (token) {
      localStorage.setItem('token', token)
      // 设置axios默认Authorization头
      http.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      localStorage.removeItem('token')
      delete http.defaults.headers.common['Authorization']
    }
  },
  setUser(state, user) {
    state.user = user
  },
  setLoading(state, loading) {
    state.loading = loading
  },
  setError(state, error) {
    state.error = error
  },
  clearAuth(state) {
    state.token = null
    state.user = null
    localStorage.removeItem('token')
    delete http.defaults.headers.common['Authorization']
  }
}

// 动作
const actions = {
  // 注册用户
  async register({ commit, dispatch }, userData) {
    commit('setLoading', true)
    commit('setError', null)
    
    try {
      const response = await http.post('/api/v1/auth/register', userData)
      
      // 注册成功后自动登录
      await dispatch('login', {
        username: userData.username,
        password: userData.password
      })
      
      return response.data
    } catch (error) {
      commit('setError', error.response?.data?.detail || '注册失败，请检查输入信息')
      throw error
    } finally {
      commit('setLoading', false)
    }
  },
  
  // 登录
  async login({ commit, dispatch }, credentials) {
    commit('setLoading', true)
    commit('setError', null)
    
    try {
      // 使用FormData格式提交 (OAuth2 password flow要求)
      const formData = new FormData()
      formData.append('username', credentials.username)
      formData.append('password', credentials.password)
      
      const response = await http.post('/api/v1/auth/login', formData)
      
      // 保存token
      commit('setToken', response.data.access_token)
      
      // 获取用户信息
      await dispatch('getCurrentUser')
      
      return response.data
    } catch (error) {
      commit('setError', error.response?.data?.detail || '登录失败')
      throw error
    } finally {
      commit('setLoading', false)
    }
  },
  
  // 注销
  logout({ commit }) {
    commit('clearAuth')
  },
  
  // 获取当前用户信息
  async getCurrentUser({ commit, state }) {
    if (!state.token) return
    
    commit('setLoading', true)
    
    try {
      const response = await http.get('/api/v1/auth/me')
      commit('setUser', response.data)
      return response.data
    } catch (error) {
      console.error('获取用户信息失败:', error)
      // 如果令牌失效，清除身份验证
      if (error.response?.status === 401) {
        commit('clearAuth')
      }
    } finally {
      commit('setLoading', false)
    }
  }
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions
} 