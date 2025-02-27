<template>
  <MainLayout>
    <div class="evaluation-page">
      <div class="container">
        <h1 class="page-title">在线评测</h1>
        
        <div class="evaluation-content">
          <!-- 左侧边栏 -->
          <div class="sidebar">
            <div class="sidebar-section">
              <h2 class="sidebar-title">我的评测</h2>
              <ul class="sidebar-list">
                <li class="sidebar-item">
                  <router-link to="/evaluation" class="sidebar-link active">评测任务</router-link>
                </li>
                <li class="sidebar-item">
                  <router-link to="/evaluation/history" class="sidebar-link">历史记录</router-link>
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
              <h2 class="content-title">评测任务</h2>
              <button @click="showTaskForm = true" class="btn">创建新任务</button>
            </div>
            
            <!-- 步骤展示 -->
            <div class="evaluation-steps">
              <div class="step-container">
                <div class="step" :class="{ 'active': currentStep >= 1 }">1</div>
                <div class="step-label">选择模型</div>
              </div>
              
              <div class="step-line" :class="{ 'active': currentStep >= 2 }"></div>
              
              <div class="step-container">
                <div class="step" :class="{ 'active': currentStep >= 2 }">2</div>
                <div class="step-label">选择评测集</div>
              </div>
              
              <div class="step-line" :class="{ 'active': currentStep >= 3 }"></div>
              
              <div class="step-container">
                <div class="step" :class="{ 'active': currentStep >= 3 }">3</div>
                <div class="step-label">开始评测</div>
              </div>
            </div>
            
            <!-- 任务表单弹窗 -->
            <div v-if="showTaskForm" class="modal">
              <div class="modal-content">
                <div class="modal-header">
                  <h2>创建评测任务</h2>
                  <button @click="showTaskForm = false" class="close-btn">&times;</button>
                </div>
                <TaskForm 
                  @cancel="showTaskForm = false" 
                  @task-created="onTaskCreated" 
                />
              </div>
            </div>
            
            <!-- 任务列表 -->
            <TaskList 
              @view-logs="viewTaskLogs" 
              ref="taskList"
              class="task-list-component"
            />
          </div>
        </div>
      </div>
      
      <!-- 日志查看器弹窗 -->
      <div v-if="currentLogTaskId" class="modal log-modal">
        <div class="modal-content log-modal-content">
          <LogViewer 
            :taskId="currentLogTaskId" 
            @close="currentLogTaskId = null" 
          />
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script>
import MainLayout from '@/layouts/MainLayout.vue'
import TaskForm from '@/components/TaskForm.vue'
import TaskList from '@/components/TaskList.vue'
import LogViewer from '@/components/LogViewer.vue'

export default {
  name: 'EvaluationView',
  components: {
    MainLayout,
    TaskForm,
    TaskList,
    LogViewer
  },
  data() {
    return {
      showTaskForm: false,
      currentStep: 1,
      currentLogTaskId: null
    }
  },
  methods: {
    onTaskCreated() {
      this.showTaskForm = false
      // 刷新任务列表
      if (this.$refs.taskList) {
        this.$refs.taskList.fetchTasks()
      }
    },
    viewTaskLogs(taskId) {
      this.currentLogTaskId = taskId
    }
  }
}
</script>

<style scoped>
.evaluation-page {
  padding: 0 0 40px;
}

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
  color: #2d3748;
}

.evaluation-content {
  display: flex;
  gap: 32px;
}

.sidebar {
  width: 250px;
  flex-shrink: 0;
}

.sidebar-section {
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  margin-bottom: 24px;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  padding: 16px;
  background-color: #f7fafc;
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-list {
  list-style: none;
  padding: 0;
}

.sidebar-item {
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-item:last-child {
  border-bottom: none;
}

.sidebar-link {
  display: block;
  padding: 12px 16px;
  color: #4a5568;
  text-decoration: none;
  transition: background-color 0.3s;
}

.sidebar-link:hover,
.sidebar-link.active {
  background-color: #ebf8ff;
  color: #3182ce;
}

.main-content {
  flex: 1;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  padding: 24px;
  position: relative;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.content-title {
  font-size: 20px;
  margin: 0;
}

.evaluation-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
}

.step-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.step {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #e2e8f0;
  color: #4a5568;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  margin-bottom: 8px;
  transition: background-color 0.3s, color 0.3s;
}

.step.active {
  background-color: #3182ce;
  color: white;
}

.step-label {
  font-size: 14px;
  color: #4a5568;
}

.step-line {
  height: 2px;
  width: 100px;
  background-color: #e2e8f0;
  margin: 0 16px;
  position: relative;
  top: -20px;
  transition: background-color 0.3s;
}

.step-line.active {
  background-color: #3182ce;
}

.task-list-component {
  margin-top: 24px;
}

/* 模态框样式 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background-color: white;
  border-radius: 8px;
  max-width: 600px;
  width: 100%;
  overflow: hidden;
  animation: fadeIn 0.3s;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #718096;
}

.log-modal-content {
  max-width: 90%;
  height: 80vh;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .evaluation-content {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
  }
  
  .step-line {
    width: 50px;
  }
  
  .modal {
    padding: 10px;
  }
  
  .log-modal-content {
    max-width: 95%;
    height: 90vh;
  }
}
</style> 