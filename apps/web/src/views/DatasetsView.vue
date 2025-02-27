<template>
  <MainLayout>
    <div class="datasets-page">
      <div class="container">
        <h1 class="page-title">我的数据集</h1>
        
        <div class="evaluation-container">
          <div class="evaluation-content">
            <!-- 左侧边栏 -->
            <div class="sidebar">
              <div class="sidebar-section">
                <h2 class="sidebar-title">我的评测</h2>
                <ul class="sidebar-list">
                  <li class="sidebar-item">
                    <router-link to="/evaluation" exact class="sidebar-link">创建评测</router-link>
                  </li>
                  <li class="sidebar-item">
                    <router-link to="/evaluation/records" class="sidebar-link">评测记录</router-link>
                  </li>
                </ul>
              </div>
              
              <div class="sidebar-section">
                <h2 class="sidebar-title">我的数据集</h2>
                <ul class="sidebar-list">
                  <li class="sidebar-item">
                    <router-link to="/evaluation/datasets" class="sidebar-link">所有数据集</router-link>
                  </li>
                  <li class="sidebar-item">
                    <router-link to="/evaluation/datasets/upload" class="sidebar-link">上传数据集</router-link>
                  </li>
                </ul>
              </div>
            </div>
            
            <!-- 右侧主内容 -->
            <div class="main-content">
              <div class="content-header">
                <h2 class="content-title">所有数据集</h2>
                <button @click="$router.push('/evaluation/datasets/upload')" class="btn btn-primary">上传新数据集</button>
              </div>
              
              <!-- 数据集列表 -->
              <div class="datasets-list">
                <p>这里将显示您的所有数据集。</p>
                <p>功能开发中，敬请期待...</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script>
import MainLayout from '@/layouts/MainLayout.vue'

export default {
  name: 'DatasetsView',
  components: {
    MainLayout
  },
  data() {
    return {
      datasets: []
    }
  },
  mounted() {
    // 这里可以添加加载数据集的逻辑
    console.log('数据集页面已加载');
  },
  methods: {
    // 这里可以添加相关方法
  }
}
</script>

<style scoped>
.datasets-page {
  padding: 0 0 40px;
}

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
  color: #2d3748;
}

.evaluation-container {
  width: 100%;
  max-width: 1600px;
  margin: 60px auto 20px;
  padding: 0 20px;
  box-sizing: border-box;
}

.evaluation-content {
  display: flex;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  padding: 0;
  overflow: hidden;
}

.sidebar {
  width: 250px;
  flex-shrink: 0;
  background-color: #f8fafc;
  padding: 24px 0;
  border-right: 1px solid #e2e8f0;
}

.sidebar-section {
  margin-bottom: 24px;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  padding: 0 24px 16px;
  color: #4a5568;
}

.sidebar-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sidebar-item {
  margin: 2px 0;
}

.sidebar-link {
  display: block;
  padding: 10px 24px;
  color: #4a5568;
  text-decoration: none;
  transition: all 0.3s;
  border-left: 3px solid transparent;
}

.sidebar-link:hover,
.router-link-active {
  background-color: #edf2f7;
  color: #3182ce;
  border-left-color: #3182ce;
}

.main-content {
  flex: 1;
  padding: 30px;
  min-height: 600px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.content-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
  color: #2d3748;
}

.datasets-list {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 30px;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.3s;
}

.btn-primary {
  background-color: #3182ce;
  color: white;
}

.btn-primary:hover {
  background-color: #2c5282;
}

@media (max-width: 1600px) {
  .evaluation-container {
    max-width: 1400px;
  }
}

@media (max-width: 1400px) {
  .evaluation-container {
    max-width: 1200px;
  }
}

@media (max-width: 1200px) {
  .evaluation-container {
    max-width: 992px;
  }
}

@media (max-width: 992px) {
  .evaluation-container {
    max-width: 768px;
    padding: 0 15px;
  }
  
  .evaluation-content {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e2e8f0;
    padding: 20px;
  }
  
  .sidebar-link {
    padding: 10px 16px;
  }
  
  .main-content {
    padding: 20px;
  }
}
</style> 