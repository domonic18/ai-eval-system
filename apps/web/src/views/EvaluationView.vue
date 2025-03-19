<template>
  <MainLayout>
    <div class="evaluation-page page-content">
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
              <div class="development-notice">功能开发中，敬请期待...</div>
              <ul class="sidebar-list disabled">
                <li class="sidebar-item disabled">
                  <span class="sidebar-link disabled">所有数据集</span>
                </li>
                <li class="sidebar-item disabled">
                  <span class="sidebar-link disabled">上传数据集</span>
                </li>
              </ul>
            </div>
          </div>
          
          <!-- 右侧主内容 -->
          <div class="main-content">
            <!-- 创建评测任务路由视图 -->
            <div v-if="$route.path === '/evaluation'">
              <div class="content-header">
                <h2 class="content-title">创建评测任务</h2>
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
              
              <!-- 评测配置表单 -->
              <div class="evaluation-form">
                <!-- 使用拆分的组件 -->
                <ModelSelectionStep 
                  v-show="currentStep === 1"
                  :initial-model-type="modelType"
                  :initial-selected-model="selectedModel"
                  :initial-custom-api-config="customApiConfig"
                  @next-step="handleModelStepComplete"
                />
                
                <DatasetSelectionStep 
                  v-show="currentStep === 2"
                  :initial-selected-datasets="selectedDatasets"
                  @next-step="handleDatasetStepComplete"
                  @prev-step="currentStep = 1"
                />
                
                <SubmitEvaluationStep 
                  v-show="currentStep === 3"
                  :model-type="modelType"
                  :selected-model="selectedModel"
                  :custom-api-config="customApiConfig"
                  :selected-datasets="selectedDatasets"
                  :model-options="modelOptions"
                  @prev-step="currentStep = 2"
                  @submit-success="handleSubmitSuccess"
                  @submit-error="handleSubmitError"
                />
              </div>
            </div>
            
            <!-- 评测记录路由视图 -->
            <div v-if="$route.path === '/evaluation/records'">
              <div class="content-header">
                <h2 class="content-title">评测记录</h2>
                <button @click="$router.push('/evaluation')" class="btn btn-primary">创建新任务</button>
              </div>
              
              <!-- 直接显示任务表格，移除额外的标题和按钮 -->
              <TaskList 
                @create-task="handleCreateTask" 
                @view-logs="viewTaskLogs" 
                @view-results="viewTaskResults"
                ref="taskList"
                :hideHeader="true"
              />
            </div>
          </div>
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
      
      <!-- 任务提交成功提示弹窗 -->
      <div v-if="showSubmitSuccess" class="modal">
        <div class="modal-content success-modal">
          <div class="modal-header">
            <h2>评测任务创建成功</h2>
            <button @click="showSubmitSuccess = false" class="close-btn">&times;</button>
          </div>
          <div class="modal-body">
            <div class="success-message">
              <i class="success-icon">✓</i>
              <p>您的评测任务已经成功提交！系统正在处理中。</p>
              <p>您可以查看<router-link to="/evaluation/records" @click="showSubmitSuccess = false">评测记录</router-link>来跟踪评测进度。</p>
            </div>
            <div class="modal-actions">
              <button @click="showSubmitSuccess = false" class="btn btn-secondary">关闭</button>
              <button @click="goToRecords" class="btn btn-primary">查看评测记录</button>
            </div>
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
      
      <!-- 结果查看器弹窗 -->
      <div v-if="currentResultTaskId" class="modal result-modal">
        <div class="modal-content result-modal-content">
          <ResultViewer 
            :taskId="currentResultTaskId" 
            @close="currentResultTaskId = null" 
          />
        </div>
      </div>
      
      <!-- 通知组件 -->
      <div v-if="notification.show" 
           :class="['notification', notification.type]"
           @click="notification.show = false">
        {{ notification.message }}
      </div>
    </div>
  </MainLayout>
</template>

<script>
import MainLayout from '@/layouts/MainLayout.vue'
import TaskForm from '@/components/TaskForm.vue'
import TaskList from '@/components/TaskList.vue'
import LogViewer from '@/components/LogViewer.vue'
import ResultViewer from '@/components/ResultViewer.vue'
import ModelSelectionStep from '@/components/evaluations/ModelSelectionStep.vue'
import DatasetSelectionStep from '@/components/evaluations/DatasetSelectionStep.vue'
import SubmitEvaluationStep from '@/components/evaluations/SubmitEvaluationStep.vue'
import { useRouter } from 'vue-router'

export default {
  name: 'EvaluationView',
  components: {
    MainLayout,
    TaskForm,
    TaskList,
    LogViewer,
    ResultViewer,
    ModelSelectionStep,
    DatasetSelectionStep,
    SubmitEvaluationStep
  },
  data() {
    return {
      showTaskForm: false,
      currentStep: 1,
      currentLogTaskId: null,
      currentResultTaskId: null,
      modelType: 'custom',
      selectedModel: null,
      customApiConfig: '',
      lastCustomApiConfig: null,
      modelOptions: [],
      selectedDatasets: [],
      showSubmitSuccess: false,
      notification: {
        show: false,
        type: 'success',
        message: ''
      }
    }
  },
  setup() {
    const router = useRouter()

    function handleCreateTask() {
      console.log('准备导航到创建评测页面');
      console.log('处理创建任务事件')
      router.push('/evaluations/create') // 或您实际的创建评测页面路径
    }

    return {
      handleCreateTask
    }
  },
  mounted() {
    // 加载模型选项供第三步使用
    this.fetchModels();
    
    if (this.$route.path === '/evaluation/records' && this.$refs.taskList) {
      this.$refs.taskList.fetchTasks();
    }
  },
  methods: {
    async fetchModels() {
      try {
        const response = await fetch('/api/v1/models', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          this.modelOptions = data.map(model => ({
            value: model.id,
            label: model.name
          }));
        } else {
          this.modelOptions = [
            { value: 'hk33smarter_api', label: 'HK33 Smarter API' },
            { value: 'gpt-4', label: 'GPT-4' },
            { value: 'claude-3', label: 'Claude 3' }
          ];
        }
      } catch (error) {
        console.error('获取模型列表失败:', error);
        this.modelOptions = [
          { value: 'hk33smarter_api', label: 'HK33 Smarter API' },
          { value: 'gpt-4', label: 'GPT-4' },
          { value: 'claude-3', label: 'Claude 3' }
        ];
      }
    },
    
    // 第一步完成的回调
    handleModelStepComplete(data) {
      this.modelType = data.modelType;
      this.selectedModel = data.selectedModel;
      this.customApiConfig = data.customApiConfig;
      this.currentStep = 2;
    },
    
    // 第二步完成的回调
    handleDatasetStepComplete(data) {
      this.selectedDatasets = data.selectedDatasets;
      this.currentStep = 3;
    },
    
    // 第三步提交成功的回调
    handleSubmitSuccess() {
      // 显示成功提示
      this.showSubmitSuccess = true;
      
      // 重置表单状态
      this.currentStep = 1;
      this.selectedModel = null;
      this.selectedDatasets = [];
      
      // 刷新任务列表
      if (this.$refs.taskList) {
        this.$refs.taskList.fetchTasks();
      }
    },
    
    // 处理提交错误
    handleSubmitError(errorMessage) {
      this.notification = {
        show: true,
        type: 'error',
        message: errorMessage
      };
      
      // 5秒后自动关闭通知
      setTimeout(() => {
        this.notification.show = false;
      }, 5000);
    },
    
    goToRecords() {
      this.showSubmitSuccess = false;
      this.$router.push('/evaluation/records');
    },
    
    onTaskCreated() {
      this.showTaskForm = false;
      // 刷新任务列表
      if (this.$route.path === '/evaluation/records' && this.$refs.taskList) {
        this.$refs.taskList.fetchTasks();
      }
    },
    viewTaskLogs(taskId) {
      this.currentLogTaskId = taskId;
    },
    viewTaskResults(taskId) {
      this.currentResultTaskId = taskId;
    }
  },
  watch: {
    // 监听路由变化
    '$route.path'(newPath) {
      if (newPath === '/evaluation/records' && this.$refs.taskList) {
        this.$refs.taskList.fetchTasks();
      }
    }
  }
}
</script>

<style scoped>
.evaluation-page {
  padding: 0 0 40px;
  width: 100%;
}

.page-title {
  font-size: 24px;
  margin-bottom: 16px;
  color: #2d3748;
}

.evaluation-container {
  width: 100%;
  max-width: 1800px;
  margin: 60px auto 20px;
  padding: 0 20px;
  box-sizing: border-box;
  padding-top: calc(var(--header-height) + 10px);
}

.evaluation-content {
  display: flex;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  padding: 0;
  overflow: visible;
  width: 100%;
}

.sidebar {
  width: 180px;
  flex-shrink: 0;
  background-color: #f8fafc;
  padding: 24px 0;
  border-right: 1px solid #e2e8f0;
}

.sidebar-section {
  margin-bottom: 20px;
}

.sidebar-title {
  font-size: 15px;
  font-weight: 600;
  padding: 0 20px 12px;
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
  padding: 8px 20px;
  color: #4a5568;
  text-decoration: none;
  transition: all 0.3s;
  border-left: 3px solid transparent;
  font-size: 14px;
}

.sidebar-link:hover,
.router-link-active {
  background-color: #edf2f7;
  color: #3182ce;
  border-left-color: #3182ce;
}

.main-content {
  flex: 1;
  padding: 25px;
  min-height: 700px;
  min-width: 0;
  overflow-x: auto;
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

.evaluation-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 40px;
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
  transition: all 0.3s;
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
  transition: all 0.3s;
}

.step-line.active {
  background-color: #3182ce;
}

.task-list-component {
  margin-top: 24px;
}

/* 评测表单样式 */
.evaluation-form {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 30px;
  margin-bottom: 30px;
}

/* 按钮样式 */
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

.btn-primary:disabled {
  background-color: #90cdf4;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #e2e8f0;
  color: #4a5568;
}

.btn-secondary:hover {
  background-color: #cbd5e0;
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

.log-modal-content, .result-modal-content {
  max-width: 90%;
  height: 80vh;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1800px) {
  .evaluation-container {
    max-width: 1600px;
  }
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
    width: 100%;
    padding: 20px;
  }
  
  .step-line {
    width: 50px;
  }
}

.sidebar-item.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.sidebar-link.disabled {
  color: #a0aec0;
  cursor: not-allowed;
  pointer-events: none;
}

.development-notice {
  font-size: 12px;
  color: #718096;
  font-style: italic;
  padding: 0 24px 8px;
}

/* 成功提示弹窗样式 */
.success-modal {
  max-width: 500px;
}

.modal-body {
  padding: 20px 24px 24px;
}

.success-message {
  text-align: center;
  margin-bottom: 24px;
}

.success-icon {
  display: inline-block;
  width: 60px;
  height: 60px;
  line-height: 60px;
  border-radius: 50%;
  background-color: #48bb78;
  color: white;
  font-size: 30px;
  margin-bottom: 16px;
}

.success-message p {
  margin: 8px 0;
  color: #4a5568;
}

.success-message a {
  color: #3182ce;
  text-decoration: none;
  font-weight: 500;
}

.modal-actions {
  display: flex;
  justify-content: space-between;
}

.notification {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 15px 25px;
  border-radius: 8px;
  color: white;
  z-index: 1000;
  cursor: pointer;
  box-shadow: 0 3px 10px rgba(0,0,0,0.1);
  animation: slideIn 0.3s ease-out;
}

.notification.success {
  background-color: #38a169;
}

.notification.error {
  background-color: #e53e3e;
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}
</style> 