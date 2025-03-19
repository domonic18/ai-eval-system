import axios from 'axios';

// 初始状态
const state = {
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || '{}'),
  status: '',
  error: null
};

// getter
const getters = {
  isAuthenticated: state => !!state.token,
  authStatus: state => state.status,
  currentUser: state => state.user,
  authError: state => state.error
};

// 突变
const mutations = {
  auth_request(state) {
    state.status = 'loading';
    state.error = null;
  },
  auth_success(state, { token, user }) {
    state.status = 'success';
    state.token = token;
    state.user = user;
    state.error = null;
  },
  auth_error(state, err) {
    state.status = 'error';
    state.error = err.response?.data?.detail || '认证失败';
  },
  logout(state) {
    state.status = '';
    state.token = '';
    state.user = {};
  }
};

// 动作
const actions = {
  // 登录动作
  async login({ commit }, user) {
    commit('auth_request');
    try {
      console.log('尝试登录:', user.username);
      const res = await axios.post('/api/v1/auth/login', {
        username: user.username,
        password: user.password
      });
      
      const token = res.data.access_token;
      const userInfo = res.data.user || { username: user.username };
      
      if (!token) {
        console.error('登录响应缺少token:', res.data);
        throw new Error('登录响应无效，缺少访问令牌');
      }
      
      console.log('登录成功，保存token');
      
      // 保存token到localStorage
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(userInfo));
      
      // 设置axios默认headers
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      
      commit('auth_success', { token, user: userInfo });
      return res;
    } catch (err) {
      console.error('登录失败:', err);
      commit('auth_error', err);
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      throw err;
    }
  },
  
  // 注册动作
  async register({ commit }, userData) {
    commit('auth_request');
    try {
      const res = await axios.post('/api/v1/auth/register', userData);
      
      // 注册成功后自动登录
      const token = res.data.access_token;
      const userInfo = res.data.user || { username: userData.username };
      
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(userInfo));
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      
      commit('auth_success', { token, user: userInfo });
      return res;
    } catch (err) {
      commit('auth_error', err);
      throw err;
    }
  },
  
  // 登出动作
  logout({ commit }) {
    // 移除token
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete axios.defaults.headers.common['Authorization'];
    commit('logout');
  },
  
  // 自动登录（从localStorage恢复会话）
  autoLogin({ commit }) {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    if (token) {
      console.log('发现已保存的token，自动恢复会话');
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      commit('auth_success', { token, user });
    } else {
      console.log('未找到保存的token，需要登录');
    }
  }
};

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions
} 