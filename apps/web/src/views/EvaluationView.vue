<template>
  <MainLayout>
    <div class="evaluation-page">
      <div class="evaluation-container">
        <h1 class="page-title">在线评测</h1>
        
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
                <div class="model-selection" v-if="currentStep === 1">
                  <h3>选择模型</h3>
                  <!-- 模型选择界面 - 改为可输入的下拉列表 -->
                  <div class="form-group">
                    <label for="modelSelect">选择或输入模型</label>
                    <div class="select-with-input">
                      <input 
                        type="text" 
                        id="modelSelect" 
                        v-model="modelInput" 
                        @input="filterModels"
                        @focus="showModelDropdown = true"
                        @blur="handleModelBlur"
                        placeholder="选择已有模型或输入新模型"
                        class="form-input"
                      />
                      <div class="dropdown-list" v-if="showModelDropdown && filteredModels.length > 0">
                        <div 
                          v-for="(model, index) in filteredModels" 
                          :key="index"
                          class="dropdown-item"
                          @mousedown="selectModelFromDropdown(model)"
                        >
                          <div class="dropdown-item-name">{{ model.name }}</div>
                          <div class="dropdown-item-desc">{{ model.description }}</div>
                          <div class="model-type-tag">{{ model.type }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 选择的模型信息 -->
                  <div class="selected-model-info" v-if="selectedModel">
                    <h4>已选模型：{{ selectedModel.name }}</h4>
                    <div class="model-details">
                      <p v-if="selectedModel.description">{{ selectedModel.description }}</p>
                      <div class="model-type">{{ selectedModel.type || '自定义' }}</div>
                    </div>
                  </div>
                  
                  <!-- 自定义模型配置 (当用户输入自定义模型时显示) -->
                  <div class="custom-model-config" v-if="isCustomModel">
                    <h4>自定义模型配置</h4>
                    <div class="form-group">
                      <label for="modelType">模型类型</label>
                      <select id="modelType" v-model="customModelType" class="form-input">
                        <option value="openai">OpenAI</option>
                        <option value="api">API</option>
                        <option value="local">本地模型</option>
                        <option value="other">其他</option>
                      </select>
                    </div>
                    
                    <div class="form-group" v-if="customModelType === 'api'">
                      <label for="apiBase">API地址</label>
                      <input type="text" id="apiBase" v-model="customModelConfig.api_base" class="form-input" placeholder="例如: https://api.example.com/v1">
                    </div>
                  </div>
                  
                  <div class="form-actions">
                    <button class="btn btn-primary" @click="goToStep(2)" :disabled="!selectedModel">下一步</button>
                  </div>
                </div>
                
                <div class="dataset-selection" v-if="currentStep === 2">
                  <h3>选择数据集</h3>
                  <!-- 数据集选择界面 -->
                  <div class="datasets-grid">
                    <!-- 这里将显示数据集选择卡片 -->
                    <div class="dataset-card" v-for="(dataset, index) in availableDatasets" :key="index"
                         @click="selectDataset(dataset)"
                         :class="{'selected': selectedDataset && selectedDataset.name === dataset.name}">
                      <div class="dataset-card-header">
                        <h4>{{ dataset.name }}</h4>
                      </div>
                      <div class="dataset-card-body">
                        <p>{{ dataset.description }}</p>
                        <div class="dataset-category">{{ dataset.category }}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div class="form-actions">
                    <button class="btn btn-secondary" @click="goToStep(1)">上一步</button>
                    <button class="btn btn-primary" @click="goToStep(3)" :disabled="!selectedDataset">下一步</button>
                  </div>
                </div>
                
                <div class="evaluation-confirmation" v-if="currentStep === 3">
                  <h3>确认评测任务</h3>
                  <!-- 确认界面 -->
                  <div class="confirmation-details">
                    <div class="detail-group">
                      <h4>选择的模型</h4>
                      <p>{{ selectedModel.name }}</p>
                      <p class="text-sm">{{ selectedModel.description }}</p>
                    </div>
                    
                    <div class="detail-group">
                      <h4>选择的数据集</h4>
                      <p>{{ selectedDataset.name }}</p>
                      <p class="text-sm">{{ selectedDataset.description }}</p>
                    </div>
                    
                    <div class="detail-group">
                      <h4>评测配置</h4>
                      <!-- 可选的评测配置选项 -->
                      <div class="form-group">
                        <label>并行度</label>
                        <select v-model="evalConfig.parallelism" class="form-input">
                          <option value="1">1</option>
                          <option value="2">2</option>
                          <option value="4">4</option>
                          <option value="8">8</option>
                        </select>
                      </div>
                    </div>
                  </div>
                  
                  <div class="form-actions">
                    <button class="btn btn-secondary" @click="goToStep(2)">上一步</button>
                    <button class="btn btn-primary" @click="submitEvaluationTask" :disabled="submitting">
                      {{ submitting ? '提交中...' : '开始评测' }}
                    </button>
                  </div>
                </div>
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
                @view-logs="viewTaskLogs" 
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
      currentLogTaskId: null,
      selectedModel: null,
      selectedDataset: null,
      evalConfig: {
        parallelism: '4'
      },
      submitting: false,
      showSubmitSuccess: false,
      modelInput: '',
      showModelDropdown: false,
      filteredModels: [],
      isCustomModel: false,
      customModelType: 'api',
      customModelConfig: {
        api_base: ''
      },
      availableModels: [
        { name: 'gpt-3.5-turbo', type: 'openai', description: 'OpenAI的GPT-3.5 Turbo模型' },
        { name: 'gpt-4', type: 'openai', description: 'OpenAI的GPT-4模型' },
        { name: 'hk33smarter_api', type: 'api', description: 'HK33 Smarter API模型' },
        { name: 'llama-7b', type: 'local', description: 'Llama 7B本地模型' }
      ],
      availableDatasets: [
        { name: 'mmlu', format: 'json', description: 'Massive Multitask Language Understanding', category: '通用能力' },
        { name: 'demo_cmmlu_chat', format: 'json', description: '中文通用语言理解测试', category: '中文理解' }
      ]
    }
  },
  mounted() {
    // 初始加载数据
    this.fetchModels();
    this.fetchDatasets();
    
    // 如果是历史记录页面，加载任务列表
    if (this.$route.path === '/evaluation/records' && this.$refs.taskList) {
      this.$refs.taskList.fetchTasks();
    }
  },
  methods: {
    fetchModels() {
      // 实际项目中应该从API获取
      console.log('获取模型列表');
      // 初始化过滤后的模型列表
      this.filteredModels = [...this.availableModels];
    },
    
    // 新增方法 - 过滤模型列表
    filterModels() {
      if (!this.modelInput) {
        this.filteredModels = [...this.availableModels];
        return;
      }
      
      const input = this.modelInput.toLowerCase();
      this.filteredModels = this.availableModels.filter(model => 
        model.name.toLowerCase().includes(input) || 
        model.description.toLowerCase().includes(input)
      );
      
      // 检查是否是自定义模型输入
      this.checkCustomModel();
    },
    
    // 新增方法 - 检查是否为自定义模型
    checkCustomModel() {
      // 如果输入的名称不在列表中，则视为自定义模型
      const isCustom = !this.availableModels.some(model => 
        model.name.toLowerCase() === this.modelInput.toLowerCase()
      );
      
      this.isCustomModel = isCustom && this.modelInput.trim() !== '';
      
      // 如果是自定义模型，更新selectedModel
      if (this.isCustomModel) {
        this.selectedModel = {
          name: this.modelInput,
          type: this.customModelType,
          description: '自定义模型',
          isCustom: true
        };
      }
    },
    
    // 新增方法 - 从下拉列表选择模型
    selectModelFromDropdown(model) {
      this.selectedModel = model;
      this.modelInput = model.name;
      this.showModelDropdown = false;
      this.isCustomModel = false;
    },
    
    // 新增方法 - 处理模型输入框失焦事件
    handleModelBlur() {
      // 使用setTimeout确保点击下拉项事件能先触发
      setTimeout(() => {
        this.showModelDropdown = false;
        
        // 如果输入为空，清除选中的模型
        if (!this.modelInput.trim()) {
          this.selectedModel = null;
          this.isCustomModel = false;
        } 
        // 如果有输入但没有从下拉列表选择，则视为自定义模型
        else if (!this.selectedModel || this.selectedModel.name !== this.modelInput) {
          this.checkCustomModel();
        }
      }, 200);
    },
    
    // 现有方法
    fetchDatasets() {
      // 实际项目中应该从API获取
      console.log('获取数据集列表');
    },
    
    goToStep(step) {
      this.currentStep = step;
    },
    
    // 更新selectModel方法
    selectModel(model) {
      this.selectedModel = model;
      this.modelInput = model.name;
      this.isCustomModel = false;
    },
    
    // 保留其他现有方法
    selectDataset(dataset) {
      this.selectedDataset = dataset;
    },
    
    submitEvaluationTask() {
      this.submitting = true;
      
      // 创建评测任务数据
      const taskData = {
        model_name: this.selectedModel.name,
        dataset_name: this.selectedDataset.name,
        model_configuration: this.selectedModel.isCustom 
          ? { type: this.customModelType, api_base: this.customModelConfig.api_base } 
          : { type: this.selectedModel.type },
        dataset_configuration: { format: this.selectedDataset.format },
        parallelism: parseInt(this.evalConfig.parallelism)
      };
      
      // 发送请求创建任务
      console.log('提交评测任务', taskData);
      
      // 实际发送HTTP请求到后端API
      fetch('/api/v1/evaluations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskData)
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`创建任务失败: ${response.status} ${response.statusText}`);
        }
        return response.json();
      })
      .then(data => {
        console.log('任务创建成功', data);
        
        // 显示成功提示
        this.showSubmitSuccess = true;
        
        // 重置任务创建状态
        this.currentStep = 1;
        this.selectedModel = null;
        this.selectedDataset = null;
        this.modelInput = '';
      })
      .catch(error => {
        console.error('创建任务错误:', error);
        alert(`创建任务失败: ${error.message}`);
      })
      .finally(() => {
        this.submitting = false;
      });
    },
    
    // 新增方法 - 跳转到评测记录
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
  width: 220px;
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
  padding: 25px;
  min-height: 600px;
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

.models-grid, .datasets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
  margin: 20px 0 30px;
}

.model-card, .dataset-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
  overflow: hidden;
}

.model-card:hover, .dataset-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.model-card.selected, .dataset-card.selected {
  border-color: #3182ce;
}

.model-card-header, .dataset-card-header {
  padding: 16px;
  background-color: #f7fafc;
  border-bottom: 1px solid #e2e8f0;
}

.model-card-body, .dataset-card-body {
  padding: 16px;
}

.model-type, .dataset-category {
  display: inline-block;
  padding: 4px 8px;
  background-color: #ebf8ff;
  color: #3182ce;
  border-radius: 4px;
  font-size: 12px;
  margin-top: 8px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 30px;
}

.confirmation-details {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
}

.detail-group {
  margin-bottom: 24px;
}

.detail-group h4 {
  margin-bottom: 8px;
  color: #4a5568;
}

.text-sm {
  font-size: 14px;
  color: #718096;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 16px;
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

.log-modal-content {
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
  
  .models-grid, .datasets-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }
}

/* 下拉列表样式 */
.select-with-input {
  position: relative;
}

.dropdown-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 300px;
  overflow-y: auto;
  background-color: white;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  z-index: 10;
}

.dropdown-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f4f8;
  transition: background-color 0.2s;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background-color: #f0f7ff;
}

.dropdown-item-name {
  font-weight: 600;
  margin-bottom: 4px;
}

.dropdown-item-desc {
  font-size: 14px;
  color: #718096;
  margin-bottom: 6px;
}

.model-type-tag {
  display: inline-block;
  background-color: #ebf8ff;
  color: #3182ce;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.selected-model-info {
  background-color: white;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
  border: 1px solid #e2e8f0;
}

.selected-model-info h4 {
  margin-top: 0;
  margin-bottom: 8px;
  color: #2d3748;
}

.model-details {
  font-size: 14px;
  color: #718096;
}

.custom-model-config {
  background-color: white;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
  border: 1px solid #e2e8f0;
}

.custom-model-config h4 {
  margin-top: 0;
  margin-bottom: 16px;
  color: #2d3748;
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
</style> 