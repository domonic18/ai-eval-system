import axios from 'axios';

// 创建axios实例
const http = axios.create({
  baseURL: '',  // 所有请求都会添加这个前缀，我们将直接使用完整路径，所以这里保留为空
  timeout: 10000,  // 请求超时时间
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// 添加请求拦截器
http.interceptors.request.use(
  config => {
    console.log('发送请求:', config.method.toUpperCase(), config.url, config.data || config.params);
    return config;
  },
  error => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 添加响应拦截器
http.interceptors.response.use(
  response => {
    console.log('响应成功:', response.status, response.config.url, response.data);
    return response;
  },
  error => {
    if (error.response) {
      console.error('响应错误:', error.response.status, error.response.config.url, error.response.data);
    } else {
      console.error('请求失败:', error.message);
    }
    return Promise.reject(error);
  }
);

export default http; 