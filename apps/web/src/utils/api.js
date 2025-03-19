import axios from 'axios';
import store from '@/store';
import router from '@/router';

// 创建axios实例
const api = axios.create({
  baseURL: '',  // API基本URL，如果是同域可以留空
  timeout: 30000  // 请求超时时间
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 从localStorage获取token
    const token = localStorage.getItem('token');
    
    // 如果有token则添加到请求头
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
      console.log('API请求添加认证头:', config.url);
    } else {
      console.log('API请求无认证头:', config.url);
    }
    
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    // 处理401错误，清除token并重定向到登录页
    if (error.response && error.response.status === 401) {
      store.dispatch('auth/logout');
      router.push('/login');
    }
    return Promise.reject(error);
  }
);

export default api; 