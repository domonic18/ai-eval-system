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
                <!-- 模型选择部分 -->
                <div class="model-selection" v-if="currentStep === 1">
                  <h3>选择模型</h3>
                  
                  <!-- 模型类型选择 -->
                  <div class="model-type-select">
                    <label>
                      <input 
                        type="radio" 
                        v-model="modelType" 
                        value="preset"
                      /> 预置模型
                    </label>
                    <label>
                      <input 
                        type="radio" 
                        v-model="modelType" 
                        value="custom" 
                      /> 自定义API
                    </label>
                  </div>

                  <!-- 多选模型下拉 -->
                  <div class="form-group">
                    <label v-if="modelType === 'preset'">选择预置模型</label>
                    <label v-else>API配置</label>
                    <Multiselect
                      v-if="modelType === 'preset'"
                      v-model="selectedModel"
                      :options="modelOptions"
                      mode="single"
                      :searchable="true"
                      placeholder="选择或搜索模型"
                      :close-on-select="true"
                    />
                    <textarea
                      v-else
                      v-model="customApiConfig"
                      class="api-config-input"
                      placeholder="输入API配置"
                      rows="4"
                    ></textarea>
                  </div>

                  <!-- 步骤导航按钮 -->
                  <div class="step-buttons">
                    <button 
                      type="button" 
                      class="btn-next"
                      @click="currentStep = 2"
                      :disabled="!canGoNext"
                    >
                      下一步
                    </button>
                  </div>
                </div>
                
                <!-- 数据集选择部分 -->
                <div class="dataset-selection" v-show="currentStep === 2">
                  <h3>选择评测数据集</h3>
                  <Multiselect
                    v-model="selectedDatasets"
                    :options="datasetOptions"
                    mode="tags"
                    :searchable="true"
                    placeholder="选择或搜索数据集"
                    :close-on-select="false"
                    label="value"
                    value-prop="value"
                  >
                    <template #option="{ option }">
                      <div class="dataset-option">
                        <div class="option-value">{{ option.value }}</div>
                        <div class="option-label">{{ option.label }}</div>
                      </div>
                    </template>
                  </Multiselect>

                  <!-- 步骤导航按钮 -->
                  <div class="step-buttons">
                    <button 
                      type="button" 
                      class="btn-prev"
                      @click="currentStep = 1"
                    >
                      上一步
                    </button>
                    <button 
                      type="button" 
                      class="btn-next"
                      @click="currentStep = 3"
                      :disabled="selectedDatasets.length === 0"
                    >
                      下一步
                    </button>
                  </div>
                </div>
                
                <div class="config-section" v-show="currentStep === 3">
                  <!-- <h3>评测配置</h3>
                  <div class="form-group">
                    <label for="config_file">配置文件路径</label>
                    <input
                      type="text"
                      id="config_file"
                      v-model="configFile"
                      placeholder="输入配置文件路径"
                    />
                  </div> -->
                  <!-- 其他配置项... -->

                  <!-- 步骤导航按钮 -->
                  <div class="step-buttons">
                    <button 
                      type="button" 
                      class="btn-prev"
                      @click="currentStep = 2"
                    >
                      上一步
                    </button>
                    <button 
                      type="button" 
                      class="btn-submit"
                      @click="submitForm"
                      :disabled="isSubmitting"
                    >
                      {{ isSubmitting ? '提交中...' : '开始评测' }}
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
import Multiselect from '@vueform/multiselect'
import '@vueform/multiselect/themes/default.css'

export default {
  name: 'EvaluationView',
  components: {
    MainLayout,
    TaskForm,
    TaskList,
    LogViewer,
    ResultViewer,
    Multiselect
  },
  data() {
    return {
      showTaskForm: false,
      currentStep: 1,
      currentLogTaskId: null,
      currentResultTaskId: null,
      modelType: 'preset',
      selectedModel: null,
      customApiConfig: '',
      lastCustomApiConfig: null,
      modelOptions: [],
      selectedDatasets: [],
      datasetOptions: [],
      defaultModels: [
        { value: 'hk33smarter_api', label: 'HK33 Smarter API' },
        { value: 'gpt-4', label: 'GPT-4' },
        { value: 'claude-3', label: 'Claude 3' }
      ],
      defaultDatasets: [
        { value: 'demo_cmmlu_chat_gen', label: '中文通用语言理解测试' },
        { value: 'demo_math_chat_gen', label: '数学问题测试集' }
      ],
      submitting: false,
      showSubmitSuccess: false,
      configFile: '',
      isSubmitting: false,
      notification: {
        show: false,
        type: 'success',
        message: ''
      }
    }
  },
  computed: {
    defaultApiConfig() {
      return `API_URL=https://guanghua-api.hk33smarter.com/v1
API_KEY=sk-xxxx
MODEL=Qwen/qwen2-1.5b-instruct`
    },
    canGoNext() {
      if (this.currentStep === 1) {
        return this.modelType === 'preset' 
          ? this.selectedModel !== null
          : this.customApiConfig.trim() !== ''
      }
      return true
    }
  },
  mounted() {
    this.fetchModels();
    this.fetchDatasets();
    
    this.loadApiConfigFromStorage();
    
    if (this.$route.path === '/evaluation/records' && this.$refs.taskList) {
      this.$refs.taskList.fetchTasks();
    }
  },
  methods: {
    loadApiConfigFromStorage() {
      try {
        const savedConfig = localStorage.getItem('evaluation_custom_api_config');
        if (savedConfig) {
          this.lastCustomApiConfig = savedConfig;
        }
        this.customApiConfig = this.lastCustomApiConfig || this.defaultApiConfig;
      } catch (error) {
        console.error('从本地存储加载配置失败:', error);
        this.customApiConfig = this.defaultApiConfig;
      }
    },
    
    saveApiConfigToStorage(config) {
      try {
        localStorage.setItem('evaluation_custom_api_config', config);
      } catch (error) {
        console.error('保存配置到本地存储失败:', error);
      }
    },
    
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
          this.modelOptions = [...this.defaultModels];
        }
      } catch (error) {
        console.error('获取模型列表失败:', error);
        this.modelOptions = [...this.defaultModels];
      }
    },
    
    async fetchDatasets() {
      try {
        const response = await fetch('/api/v1/datasets', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          this.datasetOptions = data.map(dataset => ({
            value: dataset.name,
            label: dataset.description
          }));
        } else {
          this.datasetOptions = [...this.defaultDatasets];
        }
      } catch (error) {
        console.error('获取数据集列表失败:', error);
        this.datasetOptions = [...this.defaultDatasets];
      }
    },
    
    goToStep(step) {
      this.currentStep = step;
    },
    
    async submitForm() {
      this.isSubmitting = true;
      try {
        // 处理API配置转换
        const envVars = {}
        if (this.modelType === 'custom') {
          this.customApiConfig.split('\n').forEach(line => {
            const [key, value] = line.split('=')
            if (key && value) {
              envVars[key.trim()] = value.trim()
            }
          })
        }

        // 处理数据集选择的格式转换
        // 如果selectedDatasets是对象数组，提取value属性作为字符串数组
        const datasetNames = this.selectedDatasets.map(dataset => {
          return typeof dataset === 'object' && dataset.value ? dataset.value : dataset
        });
        
        // 获取选中模型的名称
        let modelName = 'custom_api'
        if (this.modelType === 'preset' && this.selectedModel) {
          // 根据选中的模型ID查找对应的模型名称
          const selectedModelOption = this.modelOptions.find(model => model.value === this.selectedModel)
          modelName = selectedModelOption ? selectedModelOption.label : this.selectedModel
        }

        // 构建请求体
        const requestBody = {
          model_name: modelName,
          dataset_names: datasetNames,
          env_vars: envVars,
          model_configuration: {
            model_type: this.modelType,
            ...(this.modelType === 'preset' && { preset_model: this.selectedModel })
          },
          dataset_configuration: {},
          eval_config: {
            // 可以添加其他评估配置参数
            timestamp: new Date().toISOString()
          }
        }

        // 发送创建评测请求
        const response = await fetch('/api/v1/evaluations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(requestBody)
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || '创建评测任务失败')
        }

        const result = await response.json()
        
        // 显示成功提示
        this.showSubmitSuccess = true
        
        // 重置表单状态
        this.currentStep = 1
        this.selectedModel = null
        this.selectedDatasets = []
        
        // 刷新任务列表
        if (this.$refs.taskList) {
          this.$refs.taskList.fetchTasks()
        }

      } catch (error) {
        console.error('提交评测任务失败:', error)
        this.$notify({
          type: 'error',
          title: '创建任务失败',
          text: error.message || '请检查配置后重试',
          duration: 5000
        })
      } finally {
        this.isSubmitting = false
      }
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
    },
    modelType(newType) {
      if (newType === 'custom') {
        this.customApiConfig = this.lastCustomApiConfig || this.defaultApiConfig;
      }
    },
    customApiConfig(newConfig) {
      if (this.modelType === 'custom' && newConfig !== this.defaultApiConfig) {
        this.lastCustomApiConfig = newConfig;
        this.saveApiConfigToStorage(newConfig);
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
  
  .models-grid, .datasets-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }
}

/* 多选组件样式 */
.multiselect {
  @apply border-gray-300 rounded-lg;
  
  .multiselect-tag {
    @apply bg-blue-100 text-blue-800 rounded-md;
  }
  
  .multiselect-input {
    @apply border-0 focus:ring-0;
  }
}

/* 自定义模型配置布局 */
.custom-model-config {
  @apply grid grid-cols-2 gap-4 mt-6 p-4 bg-gray-50 rounded-lg;
  
  h4 {
    @apply col-span-2 text-lg font-semibold mb-4;
  }
}

/* 响应式布局 */
@media (max-width: 768px) {
  .custom-model-config {
    @apply grid-cols-1;
  }
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

.model-type-select {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.model-type-select label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.api-config-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: monospace;
}

.step-buttons {
  margin-top: 25px;
  display: flex;
  gap: 15px;
  justify-content: flex-end;
}

.btn-prev, .btn-next, .btn-submit {
  padding: 10px 25px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-prev {
  background-color: #f0f0f0;
  border: 1px solid #ddd;
}

.btn-next {
  background-color: #3182ce;
  color: white;
  border: none;
}

.btn-submit {
  background-color: #38a169;
  color: white;
  border: none;
}

.btn-next:disabled, .btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.dataset-option {
  .option-value {
    font-weight: 500;
    color: #2d3748;
  }
  .option-label {
    font-size: 12px;
    color: #718096;
    margin-top: 4px;
  }
}
</style> 