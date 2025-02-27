<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-logo">
        <img src="../assets/logo.svg" alt="司南 OpenCompass" class="logo-img">
        <h1 class="logo-text">司南 OpenCompass</h1>
      </div>
      
      <div class="register-card">
        <h2 class="register-title">注册账号</h2>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <form @submit.prevent="handleRegister" class="register-form">
          <div class="form-group">
            <label for="username" class="form-label">用户名</label>
            <input 
              type="text" 
              id="username" 
              v-model="username" 
              class="form-input" 
              required 
              minlength="3"
              maxlength="50"
              placeholder="请输入用户名（3-50个字符）"
            >
          </div>
          
          <div class="form-group">
            <label for="email" class="form-label">邮箱</label>
            <input 
              type="email" 
              id="email" 
              v-model="email" 
              class="form-input" 
              required 
              placeholder="请输入邮箱地址"
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
              minlength="6"
              placeholder="请输入密码（至少6个字符）"
            >
          </div>
          
          <div class="form-group">
            <label for="confirmPassword" class="form-label">确认密码</label>
            <input 
              type="password" 
              id="confirmPassword" 
              v-model="confirmPassword" 
              class="form-input" 
              required 
              placeholder="请再次输入密码"
            >
          </div>
          
          <div class="form-actions">
            <button type="submit" class="btn btn-primary register-btn" :disabled="loading">
              {{ loading ? '注册中...' : '注册' }}
            </button>
          </div>
        </form>
        
        <div class="form-footer">
          <p>已有账号？ <router-link to="/login">立即登录</router-link></p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'

export default defineComponent({
  name: 'RegisterView',
  setup() {
    const store = useStore()
    const router = useRouter()
    
    const username = ref('')
    const email = ref('')
    const password = ref('')
    const confirmPassword = ref('')
    const loading = ref(false)
    const error = ref(null)
    
    const handleRegister = async () => {
      // 先进行密码一致性验证
      if (password.value !== confirmPassword.value) {
        error.value = '两次输入的密码不一致'
        return
      }
      
      // 表单验证
      if (username.value.length < 3) {
        error.value = '用户名长度不能少于3个字符'
        return
      }
      
      if (password.value.length < 6) {
        error.value = '密码长度不能少于6个字符'
        return
      }
      
      loading.value = true
      error.value = null
      
      try {
        await store.dispatch('auth/register', {
          username: username.value,
          email: email.value,
          password: password.value
        })
        
        // 注册并登录成功后跳转到首页
        router.push('/')
      } catch (err) {
        error.value = err.response?.data?.detail || '注册失败，请检查输入信息'
        console.error('注册错误:', err)
      } finally {
        loading.value = false
      }
    }
    
    return {
      username,
      email,
      password,
      confirmPassword,
      loading,
      error,
      handleRegister
    }
  }
})
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f7fafc;
  padding: 20px;
}

.register-container {
  max-width: 450px;
  width: 100%;
}

.register-logo {
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

.register-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 32px;
}

.register-title {
  text-align: center;
  margin-bottom: 24px;
  font-size: 24px;
  color: #2d3748;
}

.register-form {
  margin-bottom: 24px;
}

.form-actions {
  margin-top: 24px;
}

.register-btn {
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
</style> 