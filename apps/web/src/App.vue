<script>
import { defineComponent, onMounted, nextTick, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useStore } from 'vuex'
import TaskList from './components/TaskList.vue'
import LogViewer from './components/LogViewer.vue'
import TaskForm from './components/TaskForm.vue'

export default defineComponent({
  name: 'App',
  components: {
    TaskList,
    LogViewer,
    TaskForm
  },
  setup() {
    const store = useStore()
    const router = useRouter()
    const route = useRoute()
    
    onMounted(() => {
      const token = localStorage.getItem('token')
      if (token) {
        store.commit('auth/setToken', token)
        store.dispatch('auth/getCurrentUser')
      } else {
        nextTick(() => {
          if (route && route.path !== '/login') {
            router.push('/login')
          }
        })
      }
    })
    
    return {}
  }
})
</script>

<template>
  <div id="app">
    <router-view />
  </div>
</template>

<style>

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}


body {
  font-family: 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f5f7fa;
  color: #2c3e50;
  line-height: 1.5;
}

#app {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 100vh;
} 

.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}


/* 按钮样式 */
.btn {
  display: inline-block;
  padding: 8px 16px;
  background-color: #3182ce;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.btn:hover {
  background-color: #2b6cb0;
}

.btn-secondary {
  background-color: #718096;
}

.btn-secondary:hover {
  background-color: #4a5568;
}

.btn-danger {
  background-color: #e53e3e;
}

.btn-danger:hover {
  background-color: #c53030;
}

/* 表单样式 */
.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 14px;
}

.form-input:focus {
  outline: none;
  border-color: #3182ce;
  box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.2);
}

/* 卡片样式 */
.card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  font-weight: 600;
}

.card-body {
  padding: 20px;
}

/* 表格样式 */
.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.table th {
  background-color: #f7fafc;
  font-weight: 600;
}

.table tr:hover {
  background-color: #f7fafc;
}
</style>
