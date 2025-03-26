<template>
  <div class="submit-evaluation">
    <h3>评测任务确认</h3>
    
    <div class="confirmation-container">
      <!-- 模型信息卡片 -->
      <div class="confirm-card">
        <div class="card-header">
          <div class="header-title">
            <i class="el-icon model-icon">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                <polyline points="7.5 4.21 12 6.81 16.5 4.21"></polyline>
                <polyline points="7.5 19.79 7.5 14.6 3 12"></polyline>
                <polyline points="21 12 16.5 14.6 16.5 19.79"></polyline>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                <line x1="12" y1="22.08" x2="12" y2="12"></line>
              </svg>
            </i>
            <h4>模型信息</h4>
          </div>
        </div>
        
        <div class="card-content">
          <div class="info-item">
            <span class="item-label">模型类型</span>
            <span class="item-value">{{ modelTypeText }}</span>
          </div>
          
          <!-- 根据不同的模型类型显示不同的信息 -->
          <template v-if="modelType === 'preset'">
            <div class="info-item">
              <span class="item-label">已选模型</span>
              <span class="item-value">{{ selectedModelName }}</span>
            </div>
          </template>
          
          <template v-else>
            <!-- API配置信息 -->
            <template v-if="customConfig.type === 'api'">
              <div class="info-item">
                <span class="item-label">API URL</span>
                <span class="item-value">{{ customConfig.url }}</span>
              </div>
              <div class="info-item">
                <span class="item-label">API KEY</span>
                <span class="item-value">{{ maskSecret(customConfig.key) }}</span>
              </div>
              <div class="info-item">
                <span class="item-label">MODEL</span>
                <span class="item-value">{{ customConfig.model }}</span>
              </div>
            </template>
            
            <!-- Dify配置信息 -->
            <template v-else-if="customConfig.type === 'dify'">
              <div class="info-item">
                <span class="item-label">DIFY URL</span>
                <span class="item-value">{{ customConfig.url }}</span>
              </div>
              <div class="info-item">
                <span class="item-label">DIFY API KEY</span>
                <span class="item-value">{{ maskSecret(customConfig.key) }}</span>
              </div>
              <div class="info-item">
                <span class="item-label">DIFY类型</span>
                <span class="item-value">{{ formatDifyType(customConfig.dify_type) }}</span>
              </div>
            </template>

            <!-- 添加变量信息显示 -->
            <div v-if="customConfig.input_variables && customConfig.input_variables.length > 0" class="info-item">
              <span class="item-label">输入变量</span>
              <div class="variable-list">
                <div v-for="(variable, index) in customConfig.input_variables" :key="index" class="variable-item">
                  <span>{{ variable }}</span>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
      
      <!-- 评测集信息卡片 -->
      <div class="confirm-card">
        <div class="card-header">
          <div class="header-title">
            <i class="el-icon dataset-icon">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline>
                <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path>
              </svg>
            </i>
            <h4>评测集信息</h4>
          </div>
          <span class="dataset-count">共 {{ selectedDatasets.length }} 个评测集</span>
        </div>
        
        <div class="card-content datasets-container">
          <div v-if="selectedDatasets.length === 0" class="empty-datasets">
            <p>未选择任何评测集</p>
            <button @click="goToPrevStep" class="select-datasets-btn">选择评测集</button>
          </div>
          
          <div v-else class="datasets-list">
            <div v-for="dataset in selectedDatasets" :key="dataset.id" class="dataset-item">
              <div class="dataset-name">{{ dataset.name }}</div>
              <div class="dataset-description">{{ dataset.description || '暂无描述' }}</div>
              <div class="dataset-meta" v-if="dataset.itemCount">
                <span>包含 {{ dataset.itemCount }} 条数据</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 其他配置卡片 -->
      <div class="confirm-card">
        <div class="card-header">
          <div class="header-title">
            <i class="el-icon config-icon">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </i>
            <h4>其他配置</h4>
          </div>
          <button class="expand-btn" @click="expandConfig = !expandConfig">
            {{ expandConfig ? '收起' : '展开' }}
            <i class="el-icon" :class="{ 'rotate': expandConfig }">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </i>
          </button>
        </div>
        
        <div class="card-content">
          <!-- 始终显示的选项 -->
          <div class="config-item">
            <span class="config-label">Debug模式</span>
            <el-switch v-model="config.debug" :active-value="true" :inactive-value="false" active-color="#3182ce" />
            <div class="config-description">开启后将输出的信息保存到log文件中</div>
          </div>
          
          <!-- 折叠显示的选项 -->
          <div v-if="expandConfig" class="additional-configs">
            <div class="config-item">
              <span class="config-label">详细结果输出</span>
              <el-switch v-model="config.verbose" :active-value="true" :inactive-value="false" active-color="#3182ce" />
              <div class="config-description">开启后在日志中显示详细的评估结果日志</div>
            </div>
            
            <div class="config-item">
              <span class="config-label">GPU数量</span>
              <el-input-number 
                v-model="config.gpuCount" 
                :min="0" 
                :step="1" 
                controls-position="right" 
                size="small"
                style="width: 120px; margin-left: 10px;"
              />
              <div class="config-description">每个任务使用的 GPU 数量</div>
            </div>
            
            <div class="config-item">
              <span class="config-label">空跑测试</span>
              <el-switch v-model="config.dryRun" :active-value="true" :inactive-value="false" active-color="#3182ce" />
              <div class="config-description">开启后不执行评测，用来调试命令行使用</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 提交按钮 -->
    <div class="step-buttons">
      <button 
        type="button" 
        class="btn-prev"
        @click="goToPrevStep"
      >
        上一步
      </button>
      <button 
        type="button" 
        class="btn-submit"
        @click="submitEvaluation"
        :disabled="isSubmitting || selectedDatasets.length === 0"
      >
        <span v-if="isSubmitting">
          <i class="loading-icon"></i>
          提交中...
        </span>
        <span v-else>提交评测</span>
      </button>
    </div>
  </div>
</template>

<script>
import { ElSwitch } from 'element-plus'

export default {
  name: 'SubmitEvaluationStep',
  components: {
    ElSwitch
  },
  props: {
    modelType: {
      type: String,
      required: true
    },
    selectedModel: {
      type: [String, Number, null],
      default: null
    },
    customApiConfig: {
      type: [String, Object],
      default: () => ({})
    },
    selectedDatasets: {
      type: Array,
      required: true
    },
    modelOptions: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      isSubmitting: false,
      expandConfig: false,
      config: {
        debug: false,
        verbose: true,
        gpuCount: 0,
        dryRun: false
      },
      customConfig: {
        type: 'api',
        url: '',
        key: '',
        model: '',
        dify_type: 'Chat',
        input_variables: []
      }
    }
  },
  computed: {
    modelTypeText() {
      if (this.modelType === 'preset') {
        return '我的模型';
      } else {
        // 针对自定义API类型，进一步区分API接入和Dify接入
        return this.customConfig.type === 'api' ? 'API接入' : 'Dify接入';
      }
    },
    selectedModelName() {
      if (!this.selectedModel) return '未选择';
      
      const model = this.modelOptions.find(m => m.value === this.selectedModel);
      return model ? model.label : this.selectedModel;
    }
  },
  created() {
    console.log('原始配置字符串:', this.customApiConfig);
    this.parseCustomApiConfig();
    console.log('初始化完成，自定义配置:', this.customConfig);
  },
  methods: {
    parseCustomApiConfig() {
      if (!this.customApiConfig) {
        return;
      }

      try {
        let configObj = this.customApiConfig;
        
        // 如果是字符串，尝试解析为对象
        if (typeof this.customApiConfig === 'string') {
          configObj = JSON.parse(this.customApiConfig);
        }

        // 确保配置对象存在
        if (configObj && typeof configObj === 'object') {
          if (configObj.type === 'dify') {
            // Dify 配置
            this.customConfig = {
              type: 'dify',
              url: configObj.dify_url || '',
              key: configObj.dify_api_key || '',
              dify_type: configObj.dify_type || 'Chat',
              model: '',  // Dify 不需要 model 字段
              input_variables: configObj.input_variables || []
            };
          } else {
            // API 配置
            this.customConfig = {
              type: 'api',
              url: configObj.api_url || '',
              key: configObj.api_key || '',
              model: configObj.model || '',
              dify_type: 'Chat',  // 默认值
              input_variables: []
            };
          }
        }

        console.log('解析后的配置:', {
          type: this.customConfig.type,
          url: this.customConfig.url,
          key: '***' + (this.customConfig.key ? this.customConfig.key.slice(-4) : ''),
          model: this.customConfig.model,
          dify_type: this.customConfig.dify_type
        });
      } catch (error) {
        console.error('解析配置时出错:', error);
      }
    },
    
    maskSecret(secret) {
      if (!secret) return '';
      if (secret.length <= 8) return '*'.repeat(secret.length);
      
      return secret.substring(0, 4) + '*'.repeat(secret.length - 8) + secret.substring(secret.length - 4);
    },
    
    goToPrevStep() {
      this.$emit('prev-step');
    },
    
    async submitEvaluation() {
      if (this.isSubmitting || this.selectedDatasets.length === 0) return;
      
      this.isSubmitting = true;
      
      try {
        // 构建任务名称前缀
        let taskNamePrefix = '评测任务';
        if (this.modelType === 'preset') {
          taskNamePrefix += `-预设模型-${this.selectedModelName}`;
        } else {
          const apiType = this.customConfig.type === 'dify' ? 'dify' : 'api';
          const modelName = this.customConfig.model?.replace(/\//g, '-') || '自定义模型';
          taskNamePrefix += `-${apiType}-${modelName}`;
        }

        // 根据类型构建环境变量
        const envVarsObj = this.modelType === 'preset' ? {} : 
          (this.customConfig.type === 'api' ? {
            API_URL: this.customConfig.url,
            API_KEY: this.customConfig.key,
            MODEL: this.customConfig.model
          } : {
            DIFY_TYPE: this.customConfig.dify_type,
            DIFY_URL: this.customConfig.url,
            DIFY_API_KEY: this.customConfig.key
          });

        // 构建提交的数据结构
        const evaluationData = {
          name: taskNamePrefix,
          eval_type: 'text',//目前默认为文字评测    
          model_type: this.modelType === 'preset' ? 'preset' : 'custom',
          model_name: this.modelType === 'preset' ? this.selectedModelName : 'custom_api',
          api_type: this.modelType === 'preset' ? null : this.customConfig.type,
          
          // 数据集信息
          datasets: {
            names: this.selectedDatasets.map(d => d.name || d.id),
            configuration: {}
          },
          
          // 模型配置
          model_configuration: this.modelType === 'preset' 
            ? { model_id: this.selectedModel }
            : { 
                api_type: this.customConfig.type,
                ...(this.customConfig.type === 'api' 
                  ? {
                      model: this.customConfig.model,
                      url: this.customConfig.url,
                      key: this.customConfig.key
                    }
                  : {
                      dify_type: this.customConfig.dify_type,
                      dify_url: this.customConfig.url,
                      dify_api_key: this.customConfig.key
                    })
              },
          
          // 评估配置
          eval_config: {
            debug: this.config.debug,
            verbose: this.config.verbose,
            gpu_count: this.config.gpuCount,
            dry_run: this.config.dryRun
          },
          
          // 环境变量
          env_vars: envVarsObj,
          
          // 变量配置
          input_variables: this.customConfig.input_variables || []
        };

        console.log('提交评测任务数据结构:', {
          ...evaluationData,
          env_vars: {
            ...evaluationData.env_vars,
            API_KEY: evaluationData.env_vars.API_KEY ? '***' : undefined,
            DIFY_API_KEY: evaluationData.env_vars.DIFY_API_KEY ? '***' : undefined
          }
        });
        
        // 发送API请求
        const response = await fetch('/api/v1/evaluations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(evaluationData)
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          // 错误处理逻辑
          if (typeof errorData.detail === 'string') {
            throw new Error(errorData.detail);
          } else if (Array.isArray(errorData.detail)) {
            // 将错误数组转换为可读的错误信息
            const errorMessages = errorData.detail.map(err => {
              if (typeof err === 'object') {
                // 提取错误对象中的信息
                return Object.entries(err)
                  .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
                  .join(', ');
              }
              return String(err);
            }).join('; ');
            throw new Error(`数据验证错误: ${errorMessages}`);
          } else {
            throw new Error('创建评测任务失败: ' + JSON.stringify(errorData));
          }
        }
        
        const result = await response.json();
        console.log('评测任务创建成功:', result);
        
        // 通知父组件提交成功
        this.$emit('submit-success', result);
      } catch (error) {
        console.error('提交评测任务出错:', error);
        this.$emit('submit-error', error.message || '创建评测任务失败，请稍后再试');
      } finally {
        this.isSubmitting = false;
      }
    },
    formatDifyType(type) {
      const typeMap = {
        'Chat': '聊天助手/Agent',
        'Completion': '文本生成应用',
        'Workflow': 'Chatflow/工作流'
      };
      return typeMap[type] || type;
    }
  },
  watch: {
    customApiConfig: {
      immediate: true,
      handler(newValue) {
        this.parseCustomApiConfig();
      }
    }
  }
}
</script>

<style scoped>
.submit-evaluation h3 {
  margin-bottom: 20px;
  font-size: 18px;
  color: #2d3748;
}

.confirmation-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 卡片通用样式 */
.confirm-card {
  background-color: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background-color: #f7fafc;
  border-bottom: 1px solid #e2e8f0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
}

.el-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4a5568;
}

.model-icon {
  color: #3182ce;
}

.dataset-icon {
  color: #38a169;
}

.config-icon {
  color: #d69e2e;
}

.dataset-count {
  font-size: 13px;
  color: #718096;
  background-color: #edf2f7;
  padding: 4px 8px;
  border-radius: 4px;
}

.card-content {
  padding: 20px;
}

/* 模型信息样式 */
.info-item {
  display: flex;
  margin-bottom: 12px;
  align-items: flex-start;
}

.info-item:last-child {
  margin-bottom: 0;
}

.item-label {
  width: 100px;
  font-size: 14px;
  color: #718096;
  flex-shrink: 0;
}

.item-value {
  flex: 1;
  font-size: 14px;
  color: #2d3748;
  font-weight: 500;
  word-break: break-all;
}

/* 评测集样式 */
.datasets-container {
  padding: 0;
}

.empty-datasets {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-datasets p {
  color: #a0aec0;
  margin-bottom: 16px;
}

.select-datasets-btn {
  padding: 8px 16px;
  background-color: #edf2f7;
  border: none;
  border-radius: 4px;
  color: #4a5568;
  cursor: pointer;
  transition: all 0.3s;
}

.select-datasets-btn:hover {
  background-color: #e2e8f0;
}

.datasets-list {
  max-height: 300px;
  overflow-y: auto;
}

.dataset-item {
  padding: 16px 20px;
  border-bottom: 1px solid #edf2f7;
}

.dataset-item:last-child {
  border-bottom: none;
}

.dataset-name {
  font-size: 15px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 6px;
}

.dataset-description {
  font-size: 13px;
  color: #4a5568;
  margin-bottom: 8px;
  line-height: 1.5;
}

.dataset-meta {
  font-size: 12px;
  color: #718096;
}

/* 配置项样式 */
.expand-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  color: #3182ce;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
}

.expand-btn .el-icon {
  transition: transform 0.3s;
}

.expand-btn .el-icon.rotate {
  transform: rotate(180deg);
}

.config-item {
  margin-bottom: 20px;
}

.config-item:last-child {
  margin-bottom: 15px;
}

.config-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-description {
  font-size: 12px;
  color: #718096;
  margin-top: 6px;
}

.additional-configs {
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px dashed #e2e8f0;
  animation: fadeIn 0.3s;
}

/* 按钮样式 */
.step-buttons {
  margin-top: 30px;
  display: flex;
  gap: 15px;
  justify-content: flex-end;
}

.btn-prev {
  padding: 10px 25px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #f0f0f0;
  border: 1px solid #ddd;
  font-size: 14px;
}

.btn-prev:hover {
  background-color: #e2e8f0;
}

.btn-submit {
  padding: 10px 25px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #3182ce;
  color: white;
  border: none;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 120px;
}

.btn-submit:hover:not(:disabled) {
  background-color: #2c5282;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 加载图标 */
.loading-icon {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 自定义Element Plus组件样式 */
:deep(.el-switch__core) {
  width: 40px !important;
}

/* 适配移动设备 */
@media (max-width: 768px) {
  .item-label {
    width: 80px;
  }
  
  .datasets-list {
    max-height: 250px;
  }
}

/* 数字输入框样式调整 */
.el-input-number ::v-deep(.el-input__inner) {
  padding-left: 8px;
  padding-right: 35px;
}

/* 变量配置部分样式 */
.config-section {
  margin: 20px 0;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 8px;
}

.variable-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.variable-item {
  padding: 4px 8px;
  background-color: #f0f4f8;
  border-radius: 4px;
  font-size: 12px;
  color: #4a5568;
}
</style> 