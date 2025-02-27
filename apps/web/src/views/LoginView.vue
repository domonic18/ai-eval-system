<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-logo">
        <img src="../assets/logo.png" alt="司南 OpenCompass" class="logo-img">
        <h1 class="logo-text">司南 OpenCompass</h1>
      </div>
      
      <div class="login-card">
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
        await this.$store.dispatch('auth/login', {
          username: this.username,
          password: this.password
        })
        
        // 登录成功后跳转到首页
        this.$router.push('/')
      } catch (error) {
        this.error = error.response?.data?.detail || '登录失败，请检查用户名和密码'
        console.error('登录错误:', error)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f7fafc;
  padding: 20px;
}

.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
}

.login-logo {
  text-align: center;
  margin-bottom: 24px;
}

.logo-img {
  height: 60px;
}

.logo-text {
  font-size: 24px;
  font-weight: 600;
  margin-top: 12px;
  color: #2d3748;
}

.login-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 32px;
}

.login-title {
  text-align: center;
  margin-bottom: 24px;
  font-size: 24px;
  color: #2d3748;
}

.login-form {
  width: 100%;
  max-width: 480px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.form-actions {
  margin-top: 24px;
}

.login-btn {
  width: 100%;
  padding: 12px;
  font-size: 16px;
  background-color: #3182ce;
}

.form-footer {
  text-align: center;
  font-size: 14px;
  color: #718096;
}

.form-footer a {
  color: #3182ce;
  text-decoration: none;
}

.error-message {
  background-color: #fed7d7;
  color: #c53030;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 14px;
}

@media (max-width: 768px) {
  .login-form {
    padding: 20px;
  }
}
</style>