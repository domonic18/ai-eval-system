<template>
  <div class="register-page">
    <!-- 左侧图片区域 -->
    <div class="register-banner">
      <img 
        src="@/assets/images/login-banner.png" 
        alt="评测系统展示"
        class="banner-image"
      >
    </div>

    <!-- 右侧注册表单区域 -->
    <div class="register-form-wrapper">
      <div class="register-card">
        <div class="register-logo">
          <h1 class="logo-text">OpenCompass</h1>
          <p class="system-subtitle">大模型评测系统</p>
        </div>
        
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
.register-banner {
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

/* 右侧注册区域 */
.register-form-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #ffffff;
  height: 100vh;
  overflow-y: auto;
}

.register-card {
  width: 85%;
  max-width: 400px;
  padding: 40px 30px;
}

.register-logo {
  text-align: center;
  margin-bottom: 30px;
}

.logo-img {
  height: 60px;
  margin-bottom: 10px;
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

.register-title {
  text-align: center;
  margin-bottom: 30px;
  font-size: 24px;
  color: #2d3748;
}

.register-form {
  width: 100%;
  background: transparent;
  padding: 0;
  box-shadow: none;
  max-width: none;
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

.register-btn {
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

.register-btn:hover {
  background-color: #2c5282;
}

.register-btn:disabled {
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
  .register-page {
    flex-direction: column;
  }
  
  .register-banner {
    flex: none;
    height: 30vh;
  }
  
  .register-form-wrapper {
    flex: none;
    height: 70vh;
  }
}

/* 更小屏幕适配 */
@media (max-width: 640px) {
  .register-banner {
    display: none;
  }
  
  .register-form-wrapper {
    height: 100vh;
  }
  
  .register-card {
    width: 90%;
    padding: 30px 20px;
  }
}
</style> 