<template>
  <div class="login-page">
    <!-- 左侧图片区域 -->
    <div class="login-banner">
      <img 
        src="@/assets/images/login-banner.png" 
        alt="评测系统展示"
        class="banner-image"
      >
    </div>

    <!-- 右侧登录区域 -->
    <div class="login-form-wrapper">
      <div class="login-card">
        <div class="login-logo">
          <h1 class="logo-text">OpenCompass</h1>
          <p class="system-subtitle">大模型评测系统</p>
        </div>
        
        <h2 class="login-title">登录</h2>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <form @submit.prevent="handleLogin" class="login-form">
          <div class="form-group">
            <label for="username" class="form-label">用户名</label>
            <input 
              type="text" 
              id="username" 
              v-model="username" 
              class="form-input" 
              required 
              placeholder="请输入用户名"
            >
          </div>
          
          <div class="form-group">
            <label for="password" class="form-label">密码</label>
            <input 
              type="password" 
              id="password" 
              v-model="password" 
              class="form-input" 
              required 
              placeholder="请输入密码"
            >
          </div>
          
          <div class="form-actions">
            <button type="submit" class="btn btn-primary login-btn" :disabled="loading">
              {{ loading ? '登录中...' : '登录' }}
            </button>
          </div>
        </form>
        
        <div class="form-footer">
          <p>还没有账号？ <router-link to="/register">立即注册</router-link></p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginView',
  data() {
    return {
      username: '',
      password: '',
      loading: false,
      error: null
    }
  },
  methods: {
    async handleLogin() {
      this.loading = true
      this.error = null
      
      try {
        console.log('开始登录流程')
        // 调用store中的登录方法
        const response = await this.$store.dispatch('auth/login', {
          username: this.username,
          password: this.password
        })
        
        console.log('登录API响应状态:', response.status)
        
        // 验证token是否已保存
        const savedToken = localStorage.getItem('token')
        console.log('token已保存:', !!savedToken)
        
        // 登录成功后，优先使用URL中的redirect参数跳转
        const redirectPath = this.$route.query.redirect || '/'
        console.log('准备跳转到:', redirectPath)
        
        // 确保在跳转前从后端获取最新的用户信息
        await this.$store.dispatch('auth/getCurrentUser')
        
        // 使用replace而不是push
        this.$router.replace(redirectPath)
      } catch (error) {
        console.error('登录失败:', error)
        this.error = error.response?.data?.detail || '登录失败，请检查用户名和密码'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  margin: 0;
  padding: 0;
  position: absolute;
  top: 0;
  left: 0;
}

/* 左侧图片区域 */
.login-banner {
  flex: 2;
  height: 100vh;
  overflow: hidden;
  position: relative;
}

.banner-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  position: absolute;
  top: 0;
  left: 0;
}

/* 右侧登录区域 */
.login-form-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #ffffff;
  height: 100vh;
}

.login-card {
  width: 85%;
  max-width: 400px;
  padding: 40px 30px;
}

.login-logo {
  text-align: center;
  margin-bottom: 30px;
}

.logo-text {
  font-size: 28px;
  font-weight: 600;
  margin: 0;
  color: #2d3748;
}

.system-subtitle {
  font-size: 16px;
  color: #718096;
  margin-top: 5px;
}

.login-title {
  text-align: center;
  margin-bottom: 30px;
  font-size: 24px;
  color: #2d3748;
}

.login-form {
  width: 100%;
  background: transparent;
  padding: 0;
  box-shadow: none;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #4a5568;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.form-input:focus {
  border-color: #3182ce;
  box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.2);
  outline: none;
}

.form-actions {
  margin-top: 30px;
}

.login-btn {
  width: 100%;
  padding: 12px;
  font-size: 16px;
  background-color: #3182ce;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.login-btn:hover {
  background-color: #2c5282;
}

.login-btn:disabled {
  background-color: #90cdf4;
  cursor: not-allowed;
}

.form-footer {
  text-align: center;
  font-size: 14px;
  color: #718096;
  margin-top: 25px;
}

.form-footer a {
  color: #3182ce;
  text-decoration: none;
  font-weight: 500;
}

.form-footer a:hover {
  text-decoration: underline;
}

.error-message {
  background-color: #fed7d7;
  color: #c53030;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 14px;
}

/* 移动端适配 */
@media (max-width: 1024px) {
  .login-page {
    flex-direction: column;
  }
  
  .login-banner {
    flex: none;
    height: 30vh;
  }
  
  .login-form-wrapper {
    flex: none;
    height: 70vh;
  }
}

/* 更小屏幕适配 */
@media (max-width: 640px) {
  .login-banner {
    display: none;
  }
  
  .login-form-wrapper {
    height: 100vh;
  }
  
  .login-card {
    width: 90%;
    padding: 30px 20px;
  }
}
</style>