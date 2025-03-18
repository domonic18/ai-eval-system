<template>
  <div class="model-selection">
    <h3>选择模型</h3>
    
    <!-- 模型类型选择 -->
    <div class="model-type-select">
      <div class="radio-container">
        <input 
          type="radio" 
          id="my-model"
          v-model="modelType" 
          value="preset"
        /> 
        <label for="my-model">我的模型</label>
      </div>
      <div class="radio-container">
        <input 
          type="radio" 
          id="new-api"
          v-model="modelType" 
          value="custom" 
        /> 
        <label for="new-api">新建API接入</label>
      </div>
    </div>

    <!-- 我的模型选择 -->
    <div v-if="modelType === 'preset'" class="form-section">
      <div class="form-group">
        <label>选择模型</label>
        <Multiselect
          v-model="selectedModel"
          :options="modelOptions"
          mode="single"
          :searchable="true"
          placeholder="选择或搜索模型"
          :close-on-select="true"
          class="model-select"
        >
          <template v-if="modelOptions.length === 0" #noOptions>
            <div class="no-models-message">
              模型还未创建，请前往<router-link to="/models">我的模型</router-link>创建
            </div>
          </template>
        </Multiselect>
      </div>
    </div>

    <!-- 自定义API配置 -->
    <div v-else class="form-section">
      <div class="api-type-select">
        <div class="radio-container">
          <input 
            type="radio" 
            id="api-access"
            v-model="apiType" 
            value="api"
          /> 
          <label for="api-access">API接入</label>
        </div>
        <div class="radio-container">
          <input 
            type="radio" 
            id="dify-access"
            v-model="apiType" 
            value="dify"
          /> 
          <label for="dify-access">Dify接入</label>
        </div>
      </div>
      
      <!-- API接入表单 -->
      <div v-if="apiType === 'api'" class="api-form">
        <div class="form-group">
          <label>API URL</label>
          <div class="input-with-hint">
            <input 
              type="text" 
              v-model="apiConfig.url" 
              placeholder="例如：https://api.openai.com/v1"
              class="form-input"
            />
            <button type="button" class="hint-btn" @click="showHint('url')">?</button>
          </div>
          <div v-if="hints.url" class="hint-text">
            填写LLM模型服务的API基础URL地址，例如OpenAI的https://api.openai.com/v1
          </div>
        </div>
        
        <div class="form-group">
          <label>API KEY</label>
          <div class="input-with-hint">
            <input 
              type="password" 
              v-model="apiConfig.key" 
              placeholder="请输入API KEY"
              class="form-input"
            />
            <button type="button" class="hint-btn" @click="showHint('key')">?</button>
          </div>
          <div v-if="hints.key" class="hint-text">
            填写访问API所需的密钥，通常从模型服务提供商处获取
          </div>
        </div>
        
        <div class="form-group">
          <label>MODEL</label>
          <div class="input-with-hint">
            <input 
              type="text" 
              v-model="apiConfig.model" 
              placeholder="例如：gpt-4"
              class="form-input"
            />
            <button type="button" class="hint-btn" @click="showHint('model')">?</button>
          </div>
          <div v-if="hints.model" class="hint-text">
            填写要使用的具体模型名称，例如OpenAI的gpt-4或Anthropic的claude-3-opus-20240229
          </div>
        </div>
      </div>
      
      <!-- Dify接入表单 -->
      <div v-else class="dify-form">
        <div class="form-group">
          <label>Dify应用类型</label>
          <div class="input-with-hint">
            <select v-model="difyConfig.type" class="form-select">
              <option value="Chat">Chat类型</option>
              <option value="Workflow">WorkFlow类型</option>
            </select>
            <button type="button" class="hint-btn" @click="showHint('difyType')">?</button>
          </div>
          <div v-if="hints.difyType" class="hint-text">
            选择您在Dify平台创建的应用类型
          </div>
        </div>
        
        <div class="form-group">
          <label>Dify URL</label>
          <div class="input-with-hint">
            <input 
              type="text" 
              v-model="difyConfig.url" 
              placeholder="例如：https://your-dify-instance.com"
              class="form-input"
            />
            <button type="button" class="hint-btn" @click="showHint('difyUrl')">?</button>
          </div>
          <div v-if="hints.difyUrl" class="hint-text">
            填写您的Dify实例URL地址
          </div>
        </div>
        
        <div class="form-group">
          <label>Dify API KEY</label>
          <div class="input-with-hint">
            <input 
              type="password" 
              v-model="difyConfig.key" 
              placeholder="请输入Dify API KEY"
              class="form-input"
            />
            <button type="button" class="hint-btn" @click="showHint('difyKey')">?</button>
          </div>
          <div v-if="hints.difyKey" class="hint-text">
            填写从Dify平台获取的API密钥
          </div>
        </div>
      </div>
    </div>

    <!-- 步骤导航按钮 -->
    <div class="step-buttons">
      <button 
        type="button" 
        class="btn-next"
        @click="goToNextStep"
        :disabled="!canGoNext"
      >
        下一步
      </button>
    </div>
  </div>
</template>

<script>
import Multiselect from '@vueform/multiselect'
import '@vueform/multiselect/themes/default.css'

export default {
  name: 'ModelSelectionStep',
  components: {
    Multiselect
  },
  props: {
    initialModelType: {
      type: String,
      default: 'custom'
    },
    initialSelectedModel: {
      type: [String, Number, null],
      default: null
    },
    initialCustomApiConfig: {
      type: [String, Object],
      default: ''
    }
  },
  data() {
    return {
      modelType: this.initialModelType,
      apiType: 'api', // 默认为API接入
      selectedModel: this.initialSelectedModel,
      apiConfig: {
        url: '',
        key: '',
        model: ''
      },
      difyConfig: {
        type: 'Chat', // 默认为Chat类型
        url: '',
        key: ''
      },
      hints: {
        url: false,
        key: false,
        model: false,
        difyType: false,
        difyUrl: false,
        difyKey: false
      },
      modelOptions: [],
      defaultModels: [
        { value: 'hk33smarter_api', label: 'HK33 Smarter API' }
      ]
    }
  },
  computed: {
    customApiConfig() {
      // 返回 JSON 对象
      if (this.apiType === 'api') {
        return {
          type: 'api',
          api_url: this.apiConfig.url || '',
          api_key: this.apiConfig.key || '',
          model: this.apiConfig.model || ''
        };
      } else {
        return {
          type: 'dify',
          dify_type: this.difyConfig.type || 'Chat',
          dify_url: this.difyConfig.url || '',
          dify_api_key: this.difyConfig.key || ''
        };
      }
    },
    canGoNext() {
      if (this.modelType === 'preset') {
        return this.selectedModel !== null;
      } else if (this.apiType === 'api') {
        return this.apiConfig.url.trim() !== '' && 
               this.apiConfig.key.trim() !== '' && 
               this.apiConfig.model.trim() !== '';
      } else {
        return this.difyConfig.url.trim() !== '' && 
               this.difyConfig.key.trim() !== '';
      }
    }
  },
  mounted() {
    this.fetchModels();
    this.loadApiConfigFromStorage();
    
    // 确保modelType有默认值，如果没有则设为custom
    if (!this.modelType) {
      this.modelType = 'custom';
    }
    
    // 记录当前状态用于调试
    console.log('初始模型类型:', this.modelType);
  },
  methods: {
    showHint(field) {
      // 切换提示显示状态
      this.hints[field] = !this.hints[field];
      
      // 关闭其他提示
      Object.keys(this.hints).forEach(key => {
        if (key !== field) this.hints[key] = false;
      });
    },
    
    loadApiConfigFromStorage() {
      try {
        const savedConfig = localStorage.getItem('evaluation_custom_api_config');
        if (savedConfig) {
          // 直接解析 JSON 字符串
          const configObj = JSON.parse(savedConfig);
          
          // 判断配置类型
          if (configObj.type === 'dify') {
            this.apiType = 'dify';
            this.difyConfig.type = configObj.dify_type || 'Chat';
            this.difyConfig.url = configObj.dify_url || '';
            this.difyConfig.key = configObj.dify_api_key || '';
          } else {
            this.apiType = 'api';
            this.apiConfig.url = configObj.api_url || '';
            this.apiConfig.key = configObj.api_key || '';
            this.apiConfig.model = configObj.model || '';
          }
        } else {
          // 默认值设置
          this.apiConfig = {
            url: 'https://guanghua-api.hk33smarter.com/v1',
            key: 'sk-xxxx',
            model: 'Qwen/qwen2-1.5b-instruct'
          };
        }
      } catch (error) {
        console.error('从本地存储加载配置失败:', error);
        // 设置默认值
        this.apiConfig = {
          url: 'https://guanghua-api.hk33smarter.com/v1',
          key: 'sk-xxxx',
          model: 'Qwen/qwen2-1.5b-instruct'
        };
      }
    },
    
    saveApiConfigToStorage(config) {
      try {
        // 直接存储 JSON 字符串
        localStorage.setItem('evaluation_custom_api_config', JSON.stringify(config));
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
    
    goToNextStep() {
      // 向父组件发送当前选择的状态
      this.$emit('next-step', {
        modelType: this.modelType,
        selectedModel: this.selectedModel,
        customApiConfig: this.customApiConfig
      });
    }
  },
  watch: {
    customApiConfig(newConfig) {
      // 保存配置到本地存储
      this.saveApiConfigToStorage(newConfig);
    },
    initialModelType: {
      immediate: true,
      handler(newValue) {
        if (newValue) {
          this.modelType = newValue;
          console.log('模型类型已更新:', this.modelType);
        }
      }
    }
  }
}
</script>

<style scoped>
.model-selection h3 {
  margin-bottom: 20px;
  font-size: 18px;
  color: #2d3748;
}

.model-type-select {
  display: flex;
  justify-content: flex-start;
  gap: 40px;
  margin-bottom: 25px;
  padding-bottom: 20px;
  border-bottom: 1px solid #edf2f7;
}

.api-type-select {
  display: flex;
  gap: 40px;
  margin-bottom: 20px;
}

.radio-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.radio-container input[type="radio"] {
  width: 16px;
  height: 16px;
  margin: 0;
  cursor: pointer;
}

.radio-container label {
  font-size: 14px;
  cursor: pointer;
  user-select: none;
}

.form-section {
  margin-bottom: 25px;
  animation: fadeIn 0.3s;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  font-size: 14px;
  color: #4a5568;
}

.input-with-hint {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: #4299e1;
  outline: none;
}

.form-select {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 14px;
  background-color: white;
  cursor: pointer;
}

.hint-btn {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: #e2e8f0;
  color: #4a5568;
  font-size: 12px;
  font-weight: bold;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.hint-btn:hover {
  background-color: #cbd5e0;
}

.hint-text {
  margin-top: 6px;
  padding: 8px 12px;
  background-color: #ebf8ff;
  border-left: 3px solid #4299e1;
  font-size: 12px;
  color: #2c5282;
  border-radius: 0 4px 4px 0;
  animation: fadeIn 0.3s;
}

.step-buttons {
  margin-top: 30px;
  display: flex;
  gap: 15px;
  justify-content: flex-end;
}

.btn-next {
  padding: 10px 25px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #3182ce;
  color: white;
  border: none;
  font-size: 14px;
}

.btn-next:hover:not(:disabled) {
  background-color: #2c5282;
}

.btn-next:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.api-form, .dify-form {
  animation: fadeIn 0.3s;
}

.no-models-message {
  padding: 10px;
  text-align: center;
  color: #718096;
}

.no-models-message a {
  color: #3182ce;
  text-decoration: none;
  font-weight: 500;
}

.no-models-message a:hover {
  text-decoration: underline;
}

/* 多选框样式优化 */
:deep(.multiselect) {
  border-color: #e2e8f0;
  border-radius: 4px;
  min-height: 38px;
}

:deep(.multiselect-input) {
  font-size: 14px;
}

:deep(.multiselect-placeholder) {
  color: #a0aec0;
  font-size: 14px;
}

:deep(.multiselect-option) {
  padding: 8px 12px;
}

:deep(.multiselect-option.is-selected) {
  background-color: #ebf8ff;
  color: #3182ce;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style> 