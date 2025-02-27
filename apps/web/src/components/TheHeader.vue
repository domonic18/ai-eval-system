<template>
  <header class="header">
    <div class="container header-container">
      <!-- 网站Logo -->
      <div class="logo">
        <router-link to="/">
          <img src="../assets/logo.png" alt="司南 OpenCompass" class="logo-img">
          <span class="logo-text">司南 OpenCompass</span>
        </router-link>
      </div>
      
      <!-- 导航菜单 -->
      <nav class="nav">
        <ul class="nav-list">
          <li class="nav-item">
            <router-link to="/evaluation-results" class="nav-link">评测结果</router-link>
          </li>
          <li class="nav-item">
            <router-link to="/guide" class="nav-link">使用指南</router-link>
          </li>
          <li class="nav-item">
            <router-link to="/evaluation" class="nav-link">在线评测</router-link>
          </li>
          <li class="nav-item">
            <router-link to="/arena" class="nav-link">竞技场</router-link>
          </li>
        </ul>
      </nav>
      
      <!-- 用户信息 -->
      <div class="user-info" v-if="isLoggedIn">
        <div class="user-avatar" @click="toggleUserMenu">
          <img :src="userAvatar" alt="用户头像">
          <div class="user-menu" v-if="showUserMenu">
            <div class="user-menu-header">
              <strong>{{ username }}</strong>
            </div>
            <div class="user-menu-body">
              <router-link to="/profile" class="user-menu-item">个人设置</router-link>
              <a href="#" @click.prevent="logout" class="user-menu-item">退出登录</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'TheHeader',
  data() {
    return {
      showUserMenu: false
    }
  },
  computed: {
    ...mapGetters('auth', ['isLoggedIn', 'username']),
    userAvatar() {
      return this.user?.avatar || new URL('../../assets/default-avatar.png', import.meta.url).href
    }
  },
  methods: {
    toggleUserMenu() {
      this.showUserMenu = !this.showUserMenu
    },
    logout() {
      this.$store.dispatch('auth/logout')
      this.$router.push('/login')
      this.showUserMenu = false
    }
  },
  mounted() {
    // 点击页面其他地方关闭用户菜单
    document.addEventListener('click', (e) => {
      if (!this.$el.contains(e.target)) {
        this.showUserMenu = false
      }
    })
  },
  beforeDestroy() {
    document.removeEventListener('click', this.handleClickOutside)
  }
}
</script>

<style scoped>
.header {
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
}

.header-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}

.logo {
  display: flex;
  align-items: center;
}

.logo a {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: #333;
}

.logo-img {
  height: 36px;
  margin-right: 8px;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
}

.nav {
  margin-left: 40px;
  flex-grow: 1;
}

.nav-list {
  display: flex;
  list-style: none;
}

.nav-item {
  margin-right: 32px;
}

.nav-link {
  color: #4a5568;
  text-decoration: none;
  font-size: 16px;
  position: relative;
  padding-bottom: 4px;
  transition: color 0.3s;
}

.nav-link:hover,
.router-link-active {
  color: #3182ce;
}

.router-link-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background-color: #3182ce;
}

.user-info {
  margin-left: auto;
  position: relative;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  position: relative;
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  width: 200px;
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-top: 8px;
  z-index: 101;
}

.user-menu-header {
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.user-menu-body {
  padding: 8px 0;
}

.user-menu-item {
  display: block;
  padding: 8px 16px;
  color: #4a5568;
  text-decoration: none;
  transition: background-color 0.3s;
}

.user-menu-item:hover {
  background-color: #f7fafc;
  color: #3182ce;
}
</style> 